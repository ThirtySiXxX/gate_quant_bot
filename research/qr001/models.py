"""Frozen existing baselines plus one calibration candidate; no runtime edits."""
import copy
import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from src.crypto_ml import FEATURE_NAMES, predict_probabilities
from .validation import losses


def fit_reference(kind, train, valid_from, valid_until):
    """Same specifications/export as src.ml_training, retaining a native reference.

    A test compares this frozen research wrapper with the existing exporter.
    Retaining the estimator permits independent parity checks on held-out rows.
    """
    if len(train) < 1000 or set(train.target) != {-1, 0, 1} or train.label_end.max() >= valid_from:
        raise ValueError('insufficient classes/rows or future training label')
    x, y = train[list(FEATURE_NAMES)].to_numpy(), train.target.to_numpy()
    if kind == 'logistic':
        scaler = StandardScaler().fit(x)
        native = LogisticRegression(C=.2, max_iter=500, random_state=17).fit(scaler.transform(x), y)
        exported = dict(kind=kind, mean=scaler.mean_.tolist(), scale=scaler.scale_.tolist(),
                        coef=native.coef_.tolist(), intercept=native.intercept_.tolist())
        reference = lambda rows: native.predict_proba(scaler.transform(rows))
    elif kind == 'gradient_boosting':
        native = GradientBoostingClassifier(n_estimators=60, learning_rate=.04, max_depth=2,
            min_samples_leaf=200, subsample=.8, max_features=.8, random_state=17).fit(x, y)
        trees = []
        for stage in native.estimators_:
            trees.append([dict(left=e.tree_.children_left.tolist(), right=e.tree_.children_right.tolist(),
                               feature=e.tree_.feature.tolist(), threshold=e.tree_.threshold.tolist(),
                               value=e.tree_.value[:, 0, 0].tolist()) for e in stage])
        exported = dict(kind=kind, initial_raw=np.log(native.init_.class_prior_).tolist(), trees=trees,
                        learning_rate=native.learning_rate, feature_importance=native.feature_importances_.tolist())
        reference = native.predict_proba
    else:
        raise ValueError('unsupported baseline')
    if list(native.classes_) != [-1, 0, 1]:
        raise ValueError('class order mismatch')
    exported.update(trained_until=float(train.label_end.max()), valid_from=float(valid_from),
                    valid_until=float(valid_until), train_rows=len(train))
    return exported, reference


def temperature_probabilities(p, temperature):
    if not np.isfinite(temperature) or temperature <= 0:
        raise ValueError('invalid temperature')
    raw = np.log(np.clip(p, 1e-300, 1)) / temperature
    exp = np.exp(raw - raw.max(axis=1, keepdims=True))
    return exp / exp.sum(axis=1, keepdims=True)


def calibrate(model, calibration, eval_start, embargo_hours=24, bounds=(.25, 4.)):
    if calibration.empty or calibration.label_end.max() >= eval_start - embargo_hours * 3600:
        raise ValueError('calibration label overlaps evaluation/embargo')
    if model['trained_until'] >= calibration.feature_time.min() - embargo_hours * 3600:
        raise ValueError('base model label overlaps calibration/embargo')
    p = predict_probabilities(model, calibration[list(FEATURE_NAMES)].to_numpy())
    y = calibration.target.to_numpy()
    result = minimize_scalar(lambda log_t: losses(y, temperature_probabilities(p, np.exp(log_t))).mean(),
                             bounds=tuple(np.log(bounds)), method='bounded', options={'xatol': 1e-8})
    if not result.success:
        raise ValueError('temperature optimization failed')
    temperature = float(np.exp(result.x))
    scaled = copy.deepcopy(model)
    if model['kind'] == 'gradient_boosting':
        scaled['initial_raw'] = (np.asarray(model['initial_raw']) / temperature).tolist()
        scaled['learning_rate'] /= temperature
    elif model['kind'] == 'logistic':
        scaled['coef'] = (np.asarray(model['coef']) / temperature).tolist()
        scaled['intercept'] = (np.asarray(model['intercept']) / temperature).tolist()
    else:
        raise ValueError('unsupported calibration export')
    # Calibration labels participate in fitting, so artifact availability advances.
    scaled['trained_until'] = float(calibration.label_end.max())
    return scaled, temperature
