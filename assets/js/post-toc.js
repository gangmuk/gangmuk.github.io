// post-toc.js
// Detect a "table of contents"-style bullet list at the top of the post body
// (a <ul> whose links all point to in-page #anchors). If found, rebuild it as
// a "spine + dot" sidebar in .post-toc: a thin vertical line with one dot per
// heading. Each dot is positioned at the y-coordinate proportional to its
// heading's actual position in the article — so the spacing between dots
// mirrors the spacing of the sections themselves. Labels are hidden until
// the user hovers the sidebar. A scroll handler marks passed / active dots.
(function () {
  function isTocList(ul) {
    var links = ul.querySelectorAll('a');
    if (links.length === 0) return false;
    for (var i = 0; i < links.length; i++) {
      var href = links[i].getAttribute('href') || '';
      if (href.charAt(0) !== '#') return false;
    }
    return true;
  }

  function findTocUl(article) {
    var children = article.children;
    var limit = Math.min(children.length, 5);
    for (var i = 0; i < limit; i++) {
      if (children[i].tagName === 'UL' && isTocList(children[i])) return children[i];
    }
    return null;
  }

  function flattenToc(ul, depth, out) {
    var lis = ul.children;
    for (var i = 0; i < lis.length; i++) {
      var li = lis[i];
      var a = null;
      var nested = null;
      for (var j = 0; j < li.children.length; j++) {
        var c = li.children[j];
        if (c.tagName === 'A' && !a) a = c;
        else if (c.tagName === 'UL') nested = c;
      }
      if (a) {
        out.push({
          href: a.getAttribute('href'),
          label: a.textContent.trim(),
          depth: depth,
        });
      }
      if (nested) flattenToc(nested, depth + 1, out);
    }
    return out;
  }

  function buildSidebar(items, sidebar) {
    var ul = document.createElement('ul');
    ul.className = 'post-toc-list';

    items.forEach(function (item) {
      var li = document.createElement('li');
      li.className = 'post-toc-item depth-' + Math.min(item.depth, 2);
      li.dataset.target = item.href.replace(/^#/, '');

      var a = document.createElement('a');
      a.href = item.href;

      var dot = document.createElement('span');
      dot.className = 'post-toc-dot';

      var label = document.createElement('span');
      label.className = 'post-toc-label';
      label.textContent = item.label;

      a.appendChild(dot);
      a.appendChild(label);
      li.appendChild(a);
      ul.appendChild(li);

      item.li = li; // back-reference for later layout / scroll-spy
    });

    sidebar.appendChild(ul);
    return ul;
  }

  // Position each dot at the y proportional to its heading's actual location
  // in the article. After computing the "ideal" positions, walk top-down and
  // push later dots down so consecutive dots are at least MIN_GAP px apart —
  // otherwise the labels collide on hover. The list height grows if needed
  // (the sidebar has overflow-y:auto, so it scrolls when it exceeds canvas).
  function applySpatialLayout(items, listEl, article) {
    var MIN_GAP = 18; // keeps room around each label even after font shrinks

    var entries = [];
    for (var i = 0; i < items.length; i++) {
      var id = items[i].href.replace(/^#/, '');
      var el = document.getElementById(id);
      if (el && items[i].li) entries.push({ item: items[i], el: el });
    }
    if (entries.length < 2) return;

    var firstY = entries[0].el.getBoundingClientRect().top + window.scrollY;
    var articleBottom =
      article.getBoundingClientRect().bottom + window.scrollY;
    var range = Math.max(articleBottom - firstY, 1);

    var topPad = 6;
    var bottomPad = 18;
    var canvas = Math.max(window.innerHeight - 180, 240);

    // First pass: ideal proportional positions.
    var tops = new Array(entries.length);
    for (var k = 0; k < entries.length; k++) {
      var y = entries[k].el.getBoundingClientRect().top + window.scrollY;
      var ratio = (y - firstY) / range;
      if (ratio < 0) ratio = 0;
      if (ratio > 1) ratio = 1;
      tops[k] = topPad + ratio * canvas;
    }

    // Second pass: enforce minimum gap by pushing later dots down.
    for (var m = 1; m < tops.length; m++) {
      if (tops[m] < tops[m - 1] + MIN_GAP) {
        tops[m] = tops[m - 1] + MIN_GAP;
      }
    }

    // Apply positions and size the list to fit (grows past canvas if needed).
    for (var n = 0; n < entries.length; n++) {
      var li = entries[n].item.li;
      li.style.position = 'absolute';
      li.style.top = tops[n] + 'px';
      li.style.left = '0';
      li.style.right = '0';
    }
    var lastBottom = tops[tops.length - 1] + bottomPad;
    listEl.style.height =
      Math.max(canvas + topPad + bottomPad, lastBottom) + 'px';
  }

  function setupScrollSpy(items) {
    var sections = items
      .map(function (item) {
        var id = item.href.replace(/^#/, '');
        return { id: id, el: document.getElementById(id), li: item.li };
      })
      .filter(function (s) { return s.el && s.li; });

    if (sections.length === 0) return;

    function update() {
      var threshold = window.scrollY + window.innerHeight * 0.3;
      var activeIdx = -1;
      for (var i = 0; i < sections.length; i++) {
        var top =
          sections[i].el.getBoundingClientRect().top + window.scrollY;
        if (top <= threshold) activeIdx = i;
        else break;
      }
      for (var k = 0; k < sections.length; k++) {
        var s = sections[k];
        s.li.classList.remove('is-passed', 'is-active');
        if (k < activeIdx) s.li.classList.add('is-passed');
        else if (k === activeIdx) s.li.classList.add('is-active');
      }
    }

    update();

    var ticking = false;
    function onScroll() {
      if (!ticking) {
        requestAnimationFrame(function () {
          update();
          ticking = false;
        });
        ticking = true;
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  function init() {
    var article = document.querySelector('.post-content');
    var sidebar = document.querySelector('.post-toc');
    if (!article || !sidebar) return;

    var tocUl = findTocUl(article);
    if (!tocUl) return;

    var items = flattenToc(tocUl, 0, []);
    if (items.length === 0) return;

    var listEl = buildSidebar(items, sidebar);
    tocUl.style.display = 'none';

    applySpatialLayout(items, listEl, article);
    sidebar.hidden = false;
    setupScrollSpy(items);

    // Recompute on resize (article layout may shift).
    var resizeTimer = null;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        applySpatialLayout(items, listEl, article);
      }, 150);
    });

    // Re-layout after late asset loads (images, fonts) settle the heights.
    window.addEventListener('load', function () {
      applySpatialLayout(items, listEl, article);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
