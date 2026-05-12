// post-toc.js
// Detect a "table of contents"-style bullet list at the top of the post body
// (a <ul> whose links all point to in-page #anchors). If found, clone it into
// the left sidebar (.post-toc) and hide the inline copy. Otherwise leave the
// sidebar hidden.
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
    // Check the first few top-level children for a TOC-style list. This
    // tolerates posts that lead with a stray paragraph before the TOC.
    var children = article.children;
    var limit = Math.min(children.length, 5);
    for (var i = 0; i < limit; i++) {
      var el = children[i];
      if (el.tagName === 'UL' && isTocList(el)) return el;
    }
    return null;
  }

  function init() {
    var article = document.querySelector('.post-content');
    var sidebar = document.querySelector('.post-toc');
    if (!article || !sidebar) return;

    var tocUl = findTocUl(article);
    if (!tocUl) return;

    var heading = document.createElement('h2');
    heading.className = 'post-toc-heading';
    heading.textContent = 'Contents';
    sidebar.appendChild(heading);
    sidebar.appendChild(tocUl.cloneNode(true));

    tocUl.style.display = 'none';
    sidebar.hidden = false;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
