/**
 * Menu
 */
 $("a.menu-icon").on("click", function(event) {
   var w = $(".menu");

   w.css({
     display: w.css("display") === "none"
      ? "block"
      : "none"
   });
 });

/**
 * Wechat widget
 */
function moveWidget(event) {
  var w = $("#wechat-widget");

  w.css({
    left: event.pageX - 25,
    top: event.pageY - w.height() - 60
  });
}

$("a#wechat-link").on("mouseenter", function(event) {
  $("#wechat-widget").css({ display: "block" });
  moveWidget(event);
});

$("a#wechat-link").on("mousemove", function(event) {
  moveWidget(event);
});

$("a#wechat-link").on("mouseleave", function(event) {
  $("#wechat-widget").css({ display: "none" });
});

/**
 * Expandable text sections
 */
$(document).ready(function() {
  // Wait a bit for content to render, especially code blocks
  setTimeout(function() {
    // Initialize all expandable sections
    $(".expandable").each(function() {
      var $el = $(this);
      var hasCodeBlock = $el.find("pre").length > 0;
      
      // Use different line height for code blocks vs regular text
      var lineHeight;
      if (hasCodeBlock) {
        // Code blocks typically have smaller line-height (around 1.4em)
        lineHeight = parseFloat($el.find("pre").css("line-height")) || 1.4 * 16;
      } else {
        lineHeight = parseFloat($el.css("line-height")) || 1.75 * 16;
      }
      
      var maxHeight = lineHeight * 5; // 5 lines
      
      // Temporarily remove collapsed class to measure full height
      $el.removeClass("collapsed expanded");
      var fullHeight = $el.height();
      
      // If content is longer than 5 lines, make it collapsible
      if (fullHeight > maxHeight) {
        $el.addClass("collapsed");
      } else {
        // If content is short, remove expandable functionality
        $el.removeClass("expandable");
        $el.css("cursor", "default");
      }
    });
  }, 100);
  
  // Handle click events - allow text selection in code blocks
  var mouseDownPos = { x: 0, y: 0, time: 0 };
  var isDragging = false;
  
  $(document).on("mousedown", ".expandable", function(event) {
    var $el = $(this);
    var elOffset = $el.offset();
    var elWidth = $el.width();
    var elRight = elOffset.left + elWidth;
    
    // Check if click is in the button area (button is above the block)
    var clickX = event.pageX;
    var clickY = event.pageY;
    var buttonAreaRight = elRight; // Button aligns with right edge of block
    var buttonAreaLeft = buttonAreaRight - 100; // Button area width (~100px)
    var buttonAreaBottom = elOffset.top; // Button is above the block
    var buttonAreaTop = buttonAreaBottom - 35; // Button area height (~35px)
    
    var inButtonArea = (clickX >= buttonAreaLeft && clickX <= buttonAreaRight && 
                        clickY >= buttonAreaTop && clickY <= buttonAreaBottom);
    
    if (inButtonArea) {
      // Prevent text selection in button area
      event.preventDefault();
      event.stopPropagation();
      isDragging = false;
      mouseDownPos = { x: clickX, y: clickY, time: Date.now() };
      return false;
    } else {
      // Track mouse position for text selection detection
      mouseDownPos = { x: clickX, y: clickY, time: Date.now() };
      isDragging = false;
    }
  });
  
  $(document).on("mousemove", ".expandable", function(event) {
    if (mouseDownPos.time > 0) {
      var moveDistance = Math.abs(event.pageX - mouseDownPos.x) + Math.abs(event.pageY - mouseDownPos.y);
      if (moveDistance > 5) {
        isDragging = true; // User is dragging to select text
      }
    }
  });
  
  $(document).on("mouseup", ".expandable", function() {
    // Reset after mouseup
    setTimeout(function() {
      isDragging = false;
      mouseDownPos = { x: 0, y: 0, time: 0 };
    }, 100);
  });
  
  $(document).on("click", ".expandable", function(event) {
    var $el = $(this);
    var elOffset = $el.offset();
    var elWidth = $el.width();
    var elRight = elOffset.left + elWidth;
    
    // Check if click is in the button area (button is above the block)
    var clickX = event.pageX;
    var clickY = event.pageY;
    var buttonAreaRight = elRight; // Button aligns with right edge of block
    var buttonAreaLeft = buttonAreaRight - 100; // Button area width
    var buttonAreaBottom = elOffset.top; // Button is above the block
    var buttonAreaTop = buttonAreaBottom - 35; // Button area height
    
    var inButtonArea = (clickX >= buttonAreaLeft && clickX <= buttonAreaRight && 
                        clickY >= buttonAreaTop && clickY <= buttonAreaBottom);
    
    // Don't toggle if user is selecting text (has selection or was dragging)
    var hasSelection = window.getSelection().toString().length > 0;
    
    if (inButtonArea || (!hasSelection && !isDragging)) {
      if ($el.hasClass("collapsed")) {
        // Expand
        $el.removeClass("collapsed").addClass("expanded");
      } else if ($el.hasClass("expanded")) {
        // Collapse
        $el.removeClass("expanded").addClass("collapsed");
      }
      event.preventDefault();
      event.stopPropagation();
      return false;
    }
  });
});
