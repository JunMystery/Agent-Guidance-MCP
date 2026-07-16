// Tooltip binding for chart elements carrying a `data-tip` attribute.

export function bindChartTooltip(scope) {
  const tip = scope.querySelector('#chart-tip');
  if (!tip) return;
  const wrap = scope.querySelector('.chart-wrap');
  scope.querySelectorAll('[data-tip]').forEach(node => {
    const show = () => {
      tip.textContent = node.getAttribute('data-tip');
      tip.style.opacity = '1';
    };
    const move = (e) => {
      if (!wrap) return;
      const r = wrap.getBoundingClientRect();
      tip.style.left = (e.clientX - r.left + 10) + 'px';
      tip.style.top = (e.clientY - r.top + 10) + 'px';
    };
    const hide = () => { tip.style.opacity = '0'; };
    node.addEventListener('mouseenter', show);
    node.addEventListener('mousemove', move);
    node.addEventListener('mouseleave', hide);
    node.addEventListener('focus', show);
    node.addEventListener('blur', hide);
  });
}
