"""Offline-only training/export helpers. Requires requirements-research.txt."""
import numpy as np
from .crypto_ml import FEATURE_NAMES, predict_probabilities


def fit_export(kind, train, valid_from, valid_until):
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier

    if len(train) < 1000 or set(train.target.unique()) != {-1, 0, 1}:
        raise ValueError("ML训练至少需要1000条样本且覆盖三个类别")
    if train.label_end.max() >= valid_from:
        raise ValueError("训练标签延伸进预测区间")
    X = train[list(FEATURE_NAMES)].to_numpy()
    y = train.target.to_numpy()
    if kind == "logistic":
        scaler = StandardScaler().fit(X)
        model = LogisticRegression(C=.2, max_iter=500, random_state=17).fit(scaler.transform(X), y)
        exported = dict(kind=kind, mean=scaler.mean_.tolist(), scale=scaler.scale_.tolist(),
                        coef=model.coef_.tolist(), intercept=model.intercept_.tolist())
        reference = model.predict_proba(scaler.transform(X[:500]))
    elif kind == "gradient_boosting":
        model = GradientBoostingClassifier(n_estimators=60, learning_rate=.04, max_depth=2,
            min_samples_leaf=200, subsample=.8, max_features=.8, random_state=17).fit(X, y)
        stages = []
        for estimators in model.estimators_:
            stage = []
            for estimator in estimators:
                t = estimator.tree_
                stage.append(dict(left=t.children_left.tolist(), right=t.children_right.tolist(),
                    feature=t.feature.tolist(), threshold=t.threshold.tolist(), value=t.value[:, 0, 0].tolist()))
            stages.append(stage)
        exported = dict(kind=kind, initial_raw=np.log(model.init_.class_prior_).tolist(),
                        trees=stages, learning_rate=model.learning_rate,
                        feature_importance=model.feature_importances_.tolist())
        reference = model.predict_proba(X[:500])
    else:
        raise ValueError("未知训练模型")
    assert list(model.classes_) == [-1, 0, 1]
    exported.update(valid_from=float(valid_from), valid_until=float(valid_until),
                    trained_until=float(train.label_end.max()), train_rows=len(train))
    # Runtime uses no pickle or sklearn; exported probabilities must match exactly.
    np.testing.assert_allclose(predict_probabilities(exported, X[:500]), reference, atol=1e-10, rtol=1e-9)
    return exported
