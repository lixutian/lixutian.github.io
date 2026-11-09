(function () {
  'use strict';
  document.querySelectorAll('[data-wechat-popover]').forEach(function (details) {
    var toggle = details.querySelector('.wechat-toggle');
    var panel = details.querySelector('.wechat-popover');
    var closeButton = details.querySelector('.wechat-close');
    var image = details.querySelector('.wechat-qr');
    var sidebar = details.closest('.sidebar');
    var socialList = details.closest('.author__urls');
    var saved = null;
    var frame = null;
    var hoverDevices = window.matchMedia('(hover: hover) and (pointer: fine)');
    var hoverCloseTimer = null;

    function cancelHoverClose() {
      window.clearTimeout(hoverCloseTimer);
      hoverCloseTimer = null;
    }

    function releaseContainer() {
      if (!saved) return;
      var container = saved.container;
      container.classList.remove('wechat-scroll-container');
      if (saved.height) container.style.setProperty('--wechat-available-height', saved.height);
      else container.style.removeProperty('--wechat-available-height');
      container.style.transform = saved.transform;
      container.scrollTop = saved.scrollTop;
      saved = null;
    }

    function positionBubble() {
      if (!details.open || !sidebar || !socialList) return;
      var fixed = window.getComputedStyle(sidebar).position === 'fixed';
      var container = fixed ? sidebar : socialList;
      if (!saved || saved.container !== container) {
        releaseContainer();
        saved = {
          container: container,
          height: container.style.getPropertyValue('--wechat-available-height'),
          transform: container.style.transform,
          scrollTop: container.scrollTop
        };
      }
      if (!fixed) {
        container.style.transform = saved.transform;
        var bounds = container.getBoundingClientRect();
        var offset = Math.max(0, 12 - bounds.left);
        if (bounds.right + offset > window.innerWidth - 12) {
          offset -= bounds.right + offset - (window.innerWidth - 12);
        }
        if (offset) container.style.transform = 'translateX(' + offset + 'px)';
      }
      var top = container.getBoundingClientRect().top;
      container.style.setProperty('--wechat-available-height', Math.max(96, window.innerHeight - top - 12) + 'px');
      container.classList.add('wechat-scroll-container');
      var rectangle = panel.getBoundingClientRect();
      var containerBounds = container.getBoundingClientRect();
      var masthead = document.querySelector('.masthead');
      var visibleTop = Math.max(containerBounds.top, masthead ? masthead.getBoundingClientRect().bottom : 0) + 8;
      var visibleBottom = Math.min(containerBounds.bottom, window.innerHeight - 12);
      var overflow = Math.max(0, rectangle.bottom - visibleBottom);
      // Keep the close button visible if the screen cannot fit the entire image.
      container.scrollTop += Math.min(overflow, Math.max(0, rectangle.top - visibleTop));
    }

    function schedulePosition() {
      if (frame !== null) window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(function () {
        frame = null;
        positionBubble();
      });
    }

    function close(restoreFocus) {
      cancelHoverClose();
      if (!details.open) return;
      details.open = false;
      toggle.setAttribute('aria-expanded', 'false');
      releaseContainer();
      if (restoreFocus) toggle.focus({ preventScroll: true });
    }

    // Use actual pointer capabilities, not viewport size: touch keeps native tap behavior.
    details.addEventListener('pointerenter', function (event) {
      if (!hoverDevices.matches || event.pointerType !== 'mouse') return;
      cancelHoverClose();
      details.open = true;
      toggle.setAttribute('aria-expanded', 'true');
      schedulePosition();
    });
    details.addEventListener('pointerleave', function (event) {
      if (!hoverDevices.matches || event.pointerType !== 'mouse') return;
      cancelHoverClose();
      // A short grace period avoids flicker while moving from the nickname to the QR.
      hoverCloseTimer = window.setTimeout(function () { close(false); }, 180);
    });
    hoverDevices.addEventListener('change', cancelHoverClose);

    details.addEventListener('toggle', function () {
      toggle.setAttribute('aria-expanded', String(details.open));
      if (details.open) schedulePosition();
      else releaseContainer();
    });
    closeButton.addEventListener('click', function () { close(true); });
    document.addEventListener('pointerdown', function (event) {
      if (!details.contains(event.target)) close(false);
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && details.open) {
        event.preventDefault();
        close(true);
      }
    });
    window.addEventListener('resize', schedulePosition);
    image.addEventListener('load', schedulePosition);
  });
})();
