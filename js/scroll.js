function isPartiallyInViewport(element) {
  var rect = element.getBoundingClientRect();
  var windowHeight = (window.innerHeight || document.documentElement.clientHeight);

  return (
    rect.bottom >= 0 &&
    rect.top <= windowHeight
  );
}

function showInitialImages() {
  var images = document.querySelectorAll('.collection img');
  
  images.forEach(function(image) {
    if (isPartiallyInViewport(image)) {
      image.classList.add('visible');
    }
  });
}

function showImagesOnScroll() {
  var images = document.querySelectorAll('.collection img');
  
  images.forEach(function(image) {
    if (isPartiallyInViewport(image)) {
      image.classList.add('visible');
    }
  });
}

window.addEventListener('load', showInitialImages);

window.addEventListener('scroll', showImagesOnScroll);