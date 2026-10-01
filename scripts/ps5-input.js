/* PS5's browser sends X as a pointer click at the stationary cursor. Nuvio
 * moves its own focus with the D-pad. Activate that focus when the pointer is
 * anywhere except the focused element itself. D-pad focus owns activation. */
(function () {
  'use strict';
  window.__NUVIO_PS5__ = true;
  var redirecting = false;
  document.addEventListener('click', function (event) {
    if (redirecting || event.button !== 0) return;
    var target = event.target;
    if (target && target.closest && target.closest("#__evoClose")) return;
    var focused = document.querySelector('.focusable.focused');
    if (focused && target && (target === focused || focused.contains(target))) return;
    if (!focused) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    redirecting = true;
    try { focused.click(); } finally { redirecting = false; }
  }, true);
}());
