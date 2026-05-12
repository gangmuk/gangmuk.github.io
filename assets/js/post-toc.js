// post-toc.js
// Detect a "table of contents"-style bullet list at the top of the post body
// (a <ul> whose links all point to in-page #anchors). If found, rebuild it as
// a "spine + dot" sidebar in .post-toc: a thin vertical line with one dot per
// heading. Labels are hidden until the user hovers the sidebar. A scroll-spy
// marks passed / active dots based on which section is currently in view.
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
    });

    sidebar.appendChild(ul);
    return ul;
  }

  function setupScrollSpy(items, listEl) {
    var sections = items.map(function (item) {
      var id = item.href.replace(/^#/, '');
      return {
        id: id,
        el: document.getElementById(id),
        li: listEl.querySelector('[data-target="' + CSS.escape(id) + '"]'),
      };
    }).filter(function (s) { return s.el && s.li; });

    if (sections.length === 0) return;

    function update() {
      // A section is "active" once its top has scrolled above ~30% of the viewport.
      var threshold = window.scrollY + window.innerHeight * 0.3;
      var activeIdx = -1;
      for (var i = 0; i < sections.length; i++) {
        var rect = sections[i].el.getBoundingClientRect();
        var top = rect.top + window.scrollY;
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
        requestAnimationFrame(function () { update(); ticking = false; });
        ticking = true;
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
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
    sidebar.hidden = false;
    setupScrollSpy(items, listEl);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
