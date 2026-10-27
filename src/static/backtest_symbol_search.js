/* Searches the public catalogue only; never changes the trading pool or starts a scan. */
const BacktestSymbolSearch = (() => {
  let contracts = [];
  const el = id => document.getElementById(id);
  function hide(){ el('bt-symbol-matches').hidden = true; }
  function render(){
    const input = el('bt-symbol-search'), results = el('bt-symbol-matches');
    const query = input.value.trim().toUpperCase().replace(/[-/]/g, '_');
    results.replaceChildren();
    if(!query){ hide(); return; }
    const exact = query.endsWith('_USDT') ? query : query.endsWith('USDT') ? query.slice(0,-4)+'_USDT' : query+'_USDT';
    const matches = contracts.filter(symbol => symbol.includes(query) || symbol === exact)
      .sort((a,b) => Number(b === exact)-Number(a === exact) || a.localeCompare(b)).slice(0,8);
    results.hidden = false;
    if(!matches.length){
      const note = document.createElement('p'); note.className = 'hint';
      note.textContent = contracts.length ? '目录中没有匹配项，请核对合约代码。' : '目录提示暂不可用，可直接输入币名或完整代码。';
      results.appendChild(note); return;
    }
    for(const [index,symbol] of matches.entries()){
      const button = document.createElement('button'); button.type = 'button';
      button.textContent = symbol;
      button.onclick = () => { input.value = symbol; input.focus(); hide(); };
      button.onkeydown = event => {
        if(event.key === 'Escape'){ event.preventDefault(); input.focus(); hide(); }
        else if(event.key === 'ArrowDown' || event.key === 'ArrowUp'){
          event.preventDefault();
          const next = index + (event.key === 'ArrowDown' ? 1 : -1);
          if(next < 0) input.focus(); else results.children[Math.min(next, matches.length-1)].focus();
        }
      };
      results.appendChild(button);
    }
  }
  function setContracts(items){
    contracts = [...new Set(items.map(c => c.symbol).filter(s => typeof s === 'string'))];
    if(document.activeElement === el('bt-symbol-search')) render();
  }
  function init(){
    const input = el('bt-symbol-search'), picker = el('bt-symbol-picker');
    input.oninput = render; input.onfocus = render;
    input.onkeydown = event => {
      if(event.key === 'Escape'){ event.preventDefault(); hide(); }
      else if(event.key === 'ArrowDown'){
        event.preventDefault(); render(); el('bt-symbol-matches').querySelector('button')?.focus();
      }
    };
    picker.addEventListener('focusout', event => { if(!picker.contains(event.relatedTarget)) hide(); });
  }
  return {init, setContracts};
})();
