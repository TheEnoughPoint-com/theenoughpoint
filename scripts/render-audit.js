/**
 * render-audit.js — the checks that only a rendered page can answer.
 *
 * WHY THIS EXISTS
 * scripts/check_page.py reads the HTML file. It cannot compute a colour
 * contrast, measure a table against its container, or see that two words fused
 * because a line break sat between text and an element. Every defect this file
 * tests for shipped to production at least once despite the build passing, the
 * static check passing, and the CSS looking correct in source.
 *
 * The rule this encodes: measure the rendered page, do not trust the source.
 *
 * HOW TO RUN IT
 * Evaluate this file in the page context (any driver — a browser tool, devtools
 * console, or Playwright's page.evaluate), then call:
 *
 *     renderAudit({ viewport: 390, jargon: ['mpd', 'blended rate'] })
 *
 * Returns { pass, failures[], warnings[], measured{} }. Failures are defects.
 * Warnings need a human to decide — a numeric table scrolling sideways may be
 * fine; a table of sentences doing it is not.
 *
 * WHAT IT DELIBERATELY CANNOT DO
 * Judge whether the title is comprehensible, whether the cover explains
 * anything, or whether a chart encodes the variable its caption claims. Those
 * were the defects that actually mattered on this site, and they need a reader.
 * The /preflight skill walks those separately. Do not mistake a green run here
 * for a publishable page.
 */
(function () {
  'use strict';

  /** Words whose internal capital is legitimate, so the fused-word test skips them. */
  var BRAND_WORDS = [
    'KrisFlyer', 'KrisShop', 'KrisPay', 'MileLion', 'ThankYou', 'ShopBack',
    'YouTrip', 'PayNow', 'SimplyGo', 'PayAll', 'CardUp', 'TheEnoughPoint',
    'MoneySmart', 'SingSaver', 'PayLah', 'GrabPay', 'AirAsia', 'JetBlue',
  ];

  function toLinear(v) {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  }

  function luminance(rgb) {
    var p = rgb.match(/[\d.]+/g);
    if (!p || p.length < 3) return null;
    return 0.2126 * toLinear(+p[0]) + 0.7152 * toLinear(+p[1]) + 0.0722 * toLinear(+p[2]);
  }

  function isTransparent(c) {
    if (!c) return true;
    if (c === 'transparent') return true;
    var m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return false;
    var parts = m[1].split(',');
    return parts.length === 4 && parseFloat(parts[3]) === 0;
  }

  function alphaOf(c) {
    var m = c && c.match(/rgba?\(([^)]+)\)/);
    if (!m) return 1;
    var parts = m[1].split(',');
    return parts.length === 4 ? parseFloat(parts[3]) : 1;
  }

  /** Composite a translucent colour over what sits behind it. */
  function blend(over, under) {
    var f = over.match(/[\d.]+/g).map(Number);
    var b = under.match(/[\d.]+/g).map(Number);
    var a = f.length === 4 ? f[3] : 1;
    return 'rgb(' + [0, 1, 2].map(function (i) {
      return Math.round(f[i] * a + b[i] * (1 - a));
    }).join(', ') + ')';
  }

  /** The colour actually behind an element.
   *
   *  Must composite, not just find. A 10%-opacity gold highlight over white
   *  renders as pale cream, but reading its raw rgba() as if it were solid made
   *  this audit report eight false contrast failures on a table row that is
   *  comfortably legible at 5.9:1. Collect every translucent layer up the tree,
   *  then flatten them back down over white. */
  function effectiveBackground(el) {
    var layers = [], node = el;
    var box = el.getBoundingClientRect();
    while (node && node !== document.documentElement) {
      var bg = getComputedStyle(node).backgroundColor;
      // An ancestor only counts if its paint is actually BEHIND this element.
      // An absolutely-positioned label can sit wholly outside its parent's box,
      // and treating the parent's fill as its backdrop reported eight false
      // failures on a chart whose labels sit on white beside coloured dots —
      // and very nearly turned that text white, which would have erased it.
      var ar = node.getBoundingClientRect();
      var covers = node === el || (
        box.left >= ar.left - 1 && box.right <= ar.right + 1 &&
        box.top >= ar.top - 1 && box.bottom <= ar.bottom + 1);
      if (!isTransparent(bg) && covers) {
        layers.push(bg);
        if (alphaOf(bg) === 1) break;
      }
      node = node.parentElement;
    }
    var out = 'rgb(255, 255, 255)';
    for (var i = layers.length - 1; i >= 0; i--) out = blend(layers[i], out);
    return out;
  }

  function contrast(fg, bg) {
    var a = luminance(fg), b = luminance(bg);
    if (a === null || b === null) return null;
    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  }

  /** WCAG AA: 3.0 for large text (>=24px, or >=18.66px bold), 4.5 otherwise. */
  function requiredContrast(cs) {
    var size = parseFloat(cs.fontSize);
    var weight = parseInt(cs.fontWeight, 10) || 400;
    var large = size >= 24 || (size >= 18.66 && weight >= 700);
    return large ? 3.0 : 4.5;
  }

  function describe(el) {
    var id = el.id ? '#' + el.id : '';
    var cls = (el.className && el.className.toString().trim())
      ? '.' + el.className.toString().trim().split(/\s+/).slice(0, 2).join('.')
      : '';
    return el.tagName.toLowerCase() + id + cls;
  }

  /** The nearest ancestor that paints a surface — a card, panel or table shell.
   *  Detected by what it renders rather than by class name, so it keeps working
   *  as components are added. */
  function nearestCard(el) {
    var node = el.parentElement;
    while (node && node !== document.body) {
      var cs = getComputedStyle(node);
      if (!isTransparent(cs.backgroundColor) || parseFloat(cs.borderLeftWidth) > 0) return node;
      node = node.parentElement;
    }
    return null;
  }

  /** Does this element sit inside something allowed to scroll sideways? */
  function inScrollableAncestor(el, root) {
    var node = el.parentElement;
    while (node && node !== root && node !== document.body) {
      var ox = getComputedStyle(node).overflowX;
      if (ox === 'auto' || ox === 'scroll') return node;
      node = node.parentElement;
    }
    return null;
  }

  window.renderAudit = function renderAudit(opts) {
    opts = opts || {};
    var rootSel = opts.root || '.post-content';
    var root = document.querySelector(rootSel) || document.body;
    var jargon = opts.jargon || [];
    var brandWords = BRAND_WORDS.concat(opts.allowWords || []);
    var minGutter = opts.minGutter == null ? 6 : opts.minGutter;

    var failures = [], warnings = [], measured = {};
    var vw = window.innerWidth;
    measured.viewport = vw;

    // ---- 1. the page itself must never scroll sideways -------------------
    var docW = document.documentElement.scrollWidth;
    measured.pageScrollWidth = docW;
    if (docW > vw + 1) {
      failures.push({
        check: 'page-overflow',
        detail: 'Page scrolls horizontally: ' + docW + 'px of content in a ' + vw + 'px viewport.',
      });
    }

    // ---- 2. nothing may spill past the viewport unless a scroller holds it
    var spillers = [];
    Array.prototype.forEach.call(root.querySelectorAll('*'), function (el) {
      var r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) return;
      if (r.right > vw + 1 && !inScrollableAncestor(el, root)) {
        spillers.push({ el: describe(el), right: Math.round(r.right) });
      }
    });
    if (spillers.length) {
      failures.push({
        check: 'content-spill',
        detail: spillers.length + ' element(s) extend past the viewport with nothing to scroll them.',
        elements: spillers.slice(0, 6),
      });
    }

    // ---- 3. horizontal scrollers are a fallback, not a layout ------------
    var scrollers = [];
    Array.prototype.forEach.call(root.querySelectorAll('*'), function (el) {
      var cs = getComputedStyle(el);
      if (cs.overflowX !== 'auto' && cs.overflowX !== 'scroll') return;
      if (el.scrollWidth > el.clientWidth + 1) {
        var overflowBy = el.scrollWidth - el.clientWidth;
        var text = (el.innerText || '').trim();
        // A wide numeric table is tolerable, and so is a chart — some diagrams
        // simply cannot be squeezed below a legible width. Sentences are the
        // problem: if the average table cell holds prose, scrolling sideways
        // loses the row label. Only judge elements that ARE tables; a chart has
        // no cells, and dividing by zero classed one as prose.
        var cells = el.querySelectorAll('td,th').length;
        var prose = cells > 0 && (text.split(/\s+/).length / cells) > 6;
        scrollers.push({
          el: describe(el), clientWidth: el.clientWidth, scrollWidth: el.scrollWidth,
          overflowBy: overflowBy, looksLikeProse: prose,
        });
      }
    });
    measured.horizontalScrollers = scrollers.length;
    scrollers.forEach(function (s) {
      var msg = s.el + ' scrolls sideways by ' + s.overflowBy + 'px (' +
        s.scrollWidth + ' in ' + s.clientWidth + ').';
      if (s.looksLikeProse && vw <= 480) {
        failures.push({
          check: 'prose-scroller',
          detail: msg + ' It holds sentences, so scrolling loses the row label — reflow it into cards instead.',
        });
      } else {
        warnings.push({ check: 'horizontal-scroller', detail: msg + ' Acceptable for a wide numeric table; check it reads.' });
      }
    });

    // ---- 4. contrast, including generated markers ------------------------
    var contrastFails = [];
    function checkContrast(el, pseudo) {
      var cs = getComputedStyle(el, pseudo || null);
      if (pseudo) {
        var content = cs.content;
        if (!content || content === 'none' || content === 'normal') return;
        // Decorative pseudo-elements carry an empty string: they paint a shape,
        // not text, so their colour contrast is meaningless. Counters and real
        // strings both survive this test.
        if (content === '""' || content === "''") return;
      } else {
        var hasOwnText = Array.prototype.some.call(el.childNodes, function (n) {
          return n.nodeType === 3 && n.textContent.trim().length > 1;
        });
        if (!hasOwnText) return;
      }
      if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) return;
      var box = el.getBoundingClientRect();
      if (box.width === 0 && box.height === 0) return;
      var bg = effectiveBackground(el);
      if (!isTransparent(cs.backgroundColor) && alphaOf(cs.backgroundColor) === 1) bg = cs.backgroundColor;
      var ratio = contrast(cs.color, bg);
      if (ratio === null) return;
      var need = requiredContrast(cs);
      if (ratio < need) {
        contrastFails.push({
          el: describe(el) + (pseudo || ''), ratio: Math.round(ratio * 100) / 100,
          required: need, color: cs.color, background: bg,
          sample: ((pseudo ? cs.content : el.textContent) || '').trim().slice(0, 40),
        });
      }
    }
    Array.prototype.forEach.call(root.querySelectorAll('*'), function (el) {
      checkContrast(el, null);
      checkContrast(el, '::before');
      checkContrast(el, '::after');
    });
    if (contrastFails.length) {
      failures.push({
        check: 'contrast',
        detail: contrastFails.length + ' element(s) below the WCAG AA minimum.',
        elements: contrastFails.slice(0, 8),
      });
    }

    // ---- 4b. contrast of SVG text ----------------------------------------
    // Check 4 reads getComputedStyle().color, which is exactly the property SVG
    // text does NOT paint with — it paints with `fill`. Every chart label on
    // this site is SVG text, so check 4 walked straight past all of them.
    //
    // That gap hid a real defect across fourteen components: each card set
    // background:#fff unconditionally and then lightened its palette inside a
    // prefers-color-scheme:dark block, so a dark-mode reader got pale ink on a
    // white card. On the leveraged-ETF page alone that was fifteen SVG labels
    // between 2.8:1 and 3.63:1, and check 4 reported one failure — the single
    // HTML <em> that happened to inherit the same variable.
    //
    // Size has to be scaled, not read. The font-size on an SVG label is in user
    // units; what the reader sees is that multiplied by the viewBox-to-CSS-pixel
    // ratio. A 13px label in a 720-unit viewBox rendered 358px wide is 6.5px on
    // a phone, and treating it as 13px would apply the wrong threshold.
    var svgTextFails = [];
    Array.prototype.forEach.call(root.querySelectorAll('svg'), function (svg) {
      var vb = svg.viewBox && svg.viewBox.baseVal;
      var box = svg.getBoundingClientRect();
      var scale = (vb && vb.width && box.width) ? box.width / vb.width : 1;
      var bg = effectiveBackground(svg);
      Array.prototype.forEach.call(svg.querySelectorAll('text, tspan'), function (t) {
        if (t.tagName.toLowerCase() === 'text' && t.querySelector('tspan')) return;
        var txt = (t.textContent || '').trim();
        if (!txt) return;
        var cs = getComputedStyle(t);
        if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) return;
        var r = t.getBoundingClientRect();
        if (!r.width && !r.height) return;
        var fill = cs.fill;
        if (!fill || fill === 'none' || isTransparent(fill)) return;
        var ratio = contrast(fill, bg);
        if (ratio === null) return;
        var px = parseFloat(cs.fontSize) * scale;
        var weight = parseInt(cs.fontWeight, 10) || 400;
        var need = (px >= 24 || (px >= 18.66 && weight >= 700)) ? 3.0 : 4.5;
        if (ratio < need) {
          svgTextFails.push({
            el: describe(t), ratio: Math.round(ratio * 100) / 100, required: need,
            renderedPx: Math.round(px * 10) / 10, color: fill, background: bg,
            sample: txt.slice(0, 40),
          });
        }
      });
    });
    if (svgTextFails.length) {
      failures.push({
        check: 'svg-text-contrast',
        detail: svgTextFails.length + ' SVG label(s) below the WCAG AA minimum.',
        elements: svgTextFails.slice(0, 8),
      });
    }

    // ---- 5. fused words from .astro whitespace collapse ------------------
    // Measured structurally, not lexically. The first version matched a
    // lowercase letter followed by a capital and needed a brand allowlist to
    // stay quiet — it still flagged CapitaLand, OneMap, iHerb, ShopFest,
    // LionGlobal and VanEck as defects across the archive. Every one was a
    // single text node and therefore never a fusion at all.
    //
    // The real bug has a shape: a line break between text and an element in a
    // .astro template collapses the space, so two text nodes from DIFFERENT
    // elements end up rendered on the same line with no gap between them. That
    // is testable directly by measuring where the characters land, and it needs
    // no vocabulary at all.
    function charRect(node, atEnd) {
      var t = node.textContent;
      var i = atEnd ? t.length - 1 : 0;
      while (i >= 0 && i < t.length && !/\S/.test(t.charAt(i))) i += atEnd ? -1 : 1;
      if (i < 0 || i >= t.length) return null;
      var range = document.createRange();
      range.setStart(node, i);
      range.setEnd(node, i + 1);
      var r = range.getBoundingClientRect();
      return r.width || r.height ? r : null;
    }

    var fused = [];
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var prev = null;
    while (walker.nextNode()) {
      var node = walker.currentNode;
      var t = node.textContent;
      if (!t || !t.trim()) continue;
      if (prev && prev.node.parentElement !== node.parentElement) {
        var endsWord = /[\w.,;:!?)]$/.test(prev.text.replace(/\s+$/, ''));
        var startsWord = /^[\w(]/.test(t.replace(/^\s+/, ''));
        var noGapInSource = !/\s$/.test(prev.text) && !/^\s/.test(t);
        if (endsWord && startsWord && noGapInSource) {
          var r1 = charRect(prev.node, true), r2 = charRect(node, false);
          // Same line, and the ink actually touches.
          if (r1 && r2 && Math.abs(r1.top - r2.top) < 4 && (r2.left - r1.right) < 1.5 && r2.left >= r1.left) {
            fused.push(prev.text.replace(/\s+$/, '').slice(-16) + '|' + t.replace(/^\s+/, '').slice(0, 16));
          }
        }
      }
      prev = { node: node, text: t };
    }
    if (fused.length) {
      failures.push({
        check: 'fused-words',
        detail: "Words render with no space between them, across an element boundary. In .astro that is a line break sitting between text and a tag: put the space on the same line, or emit one explicitly.",
        elements: fused.slice(0, 10),
      });
    }

    // ---- 6. jargon the piece said it had removed -------------------------
    if (jargon.length) {
      var text = (root.innerText || '').replace(/ /g, ' ');
      var found = {};
      jargon.forEach(function (w) {
        var re = new RegExp('\\b' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'gi');
        var n = (text.match(re) || []).length;
        if (n) found[w] = n;
      });
      measured.jargon = found;
      if (Object.keys(found).length) {
        failures.push({
          check: 'jargon',
          detail: 'Terms on the banned list appear in the rendered page.',
          elements: found,
        });
      }
    }

    // ---- 7. ink must not sit on a card edge ------------------------------
    // Measure where the TEXT actually lands, not the element box. A <td> with
    // its own padding legitimately starts at its container's edge while the
    // words inside are comfortably inset — measuring boxes flagged 58 such
    // cells as defects on this site's own pages. A Range gives the ink.
    var tight = [];
    Array.prototype.forEach.call(root.querySelectorAll('p, li, td, h2, h3, div'), function (el) {
      var textNode = Array.prototype.filter.call(el.childNodes, function (n) {
        return n.nodeType === 3 && n.textContent.trim().length > 1;
      })[0];
      if (!textNode) return;
      var card = nearestCard(el);
      if (!card) return;
      var range = document.createRange();
      range.selectNodeContents(textNode);
      var r = range.getBoundingClientRect();
      if (r.width === 0) return;
      var cr = card.getBoundingClientRect();
      var left = r.left - cr.left, right = cr.right - r.right;
      if (left < minGutter || right < minGutter) {
        tight.push({
          el: describe(el), card: describe(card),
          left: Math.round(left), right: Math.round(right),
          sample: textNode.textContent.trim().slice(0, 32),
        });
      }
    });
    if (tight.length) {
      warnings.push({
        check: 'tight-gutter',
        detail: tight.length + ' element(s) sit within ' + minGutter + 'px of their container edge.',
        elements: tight.slice(0, 5),
      });
    }

    // ---- 8. no rendered link may carry a serialised undefined ------------
    // Four articles shipped share links whose prefilled text began with the
    // literal word "undefined" — a bare component call site, invisible to
    // every static check and to this audit's other assertions, caught in a
    // real WhatsApp compose box (22 Aug 2026). Inside an href, "undefined"
    // or "null" is always a serialised bug, never content. Page-wide scan,
    // deliberately wider than `root`: the defect lived in a share row that a
    // template may render outside the article body.
    var badHrefs = [];
    Array.prototype.forEach.call(document.querySelectorAll('a[href]'), function (a) {
      var h = a.getAttribute('href') || '';
      if (/\bundefined\b|\bnull\b/.test(h)) {
        badHrefs.push({ el: describe(a), href: h.slice(0, 90) });
      }
    });
    if (badHrefs.length) {
      failures.push({
        check: 'href-undefined',
        detail: badHrefs.length + ' link(s) contain a serialised undefined/null — a prop missing at some call site.',
        elements: badHrefs.slice(0, 6),
      });
    }

    // ---- 9. absolutely-positioned labels must not overlap ----------------
    // Chart labels are HTML positioned over plots by percentage. Twice in one
    // session two of them collided — six year ticks across a 200px phone plot,
    // then two gutter values on a short plot — and both reached human review
    // before anything caught them. Any two absolutely-positioned text labels
    // whose rectangles genuinely intersect (beyond a 2px kiss) are a defect.
    var absLabels = [];
    Array.prototype.forEach.call(root.querySelectorAll('*'), function (el) {
      var cs = getComputedStyle(el);
      if (cs.position !== 'absolute') return;
      if (cs.display === 'none' || cs.visibility === 'hidden') return;
      var text = (el.innerText || '').trim();
      if (!text) return;
      // Leaf labels only: a positioned container holding other positioned
      // labels is layout, and its box legitimately spans its children.
      var holdsAbs = Array.prototype.some.call(el.querySelectorAll('*'), function (c) {
        return getComputedStyle(c).position === 'absolute';
      });
      if (holdsAbs) return;
      var r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      absLabels.push({ d: describe(el), t: text.slice(0, 18), r: r });
    });
    var labelClashes = [];
    for (var li = 0; li < absLabels.length; li++) {
      for (var lj = li + 1; lj < absLabels.length; lj++) {
        var LA = absLabels[li].r, LB = absLabels[lj].r;
        var lox = Math.min(LA.right, LB.right) - Math.max(LA.left, LB.left);
        var loy = Math.min(LA.bottom, LB.bottom) - Math.max(LA.top, LB.top);
        if (lox > 2 && loy > 2) {
          labelClashes.push({
            a: absLabels[li].d + ' "' + absLabels[li].t + '"',
            b: absLabels[lj].d + ' "' + absLabels[lj].t + '"',
          });
        }
      }
    }
    if (labelClashes.length) {
      failures.push({
        check: 'label-overlap',
        detail: labelClashes.length + ' pair(s) of absolutely-positioned labels overlap — reposition, thin, or hide one at this width.',
        elements: labelClashes.slice(0, 6),
      });
    }

    // ---- 10. title length ------------------------------------------------
    var title = (document.title || '').trim();
    measured.title = title;
    measured.titleLength = title.length;
    if (title.length > 60) {
      warnings.push({
        check: 'title-length',
        detail: 'Title is ' + title.length + ' characters; search results truncate near 60. Confirm the keyword half survives.',
      });
    }

    return {
      pass: failures.length === 0,
      failures: failures,
      warnings: warnings,
      measured: measured,
    };
  };
})();
