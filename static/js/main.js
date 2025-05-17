(function ($) {
    "use strict";
    
    // Dropdown on mouse hover
    $(document).ready(function () {
        function toggleNavbarMethod() {
            if ($(window).width() > 992) {
                $('.navbar .dropdown').on('mouseover', function () {
                    $('.dropdown-toggle', this).trigger('click');
                }).on('mouseout', function () {
                    $('.dropdown-toggle', this).trigger('click').blur();
                });
            } else {
                $('.navbar .dropdown').off('mouseover').off('mouseout');
            }
        }
        toggleNavbarMethod();
        $(window).resize(toggleNavbarMethod);
    });
    
    
    // Back to top button
    $(window).scroll(function () {
        if ($(this).scrollTop() > 100) {
            $('.back-to-top').fadeIn('slow');
        } else {
            $('.back-to-top').fadeOut('slow');
        }
    });
    $('.back-to-top').click(function () {
        $('html, body').animate({scrollTop: 0}, 1500, 'easeInOutExpo');
        return false;
    });


    // Vendor carousel
    $('.vendor-carousel').owlCarousel({
        loop: true,
        margin: 29,
        nav: false,
        autoplay: true,
        smartSpeed: 1000,
        responsive: {
            0:{
                items:2
            },
            576:{
                items:3
            },
            768:{
                items:4
            },
            992:{
                items:5
            },
            1200:{
                items:6
            }
        }
    });


    // Related carousel
    $('.related-carousel').owlCarousel({
        loop: true,
        margin: 29,
        nav: true,
        autoplay: true,
        smartSpeed: 1000,
        responsive: {
            0:{
                items:1
            },
            576:{
                items:2
            },
            768:{
                items:3
            },
            992:{
                items:4
            }
        }
    });


    // Product Quantity
    $('.quantity button').on('click', function () {
        var button = $(this);
        var oldValue = button.parent().parent().find('input').val();
        if (button.hasClass('btn-plus')) {
            var newVal = parseFloat(oldValue) + 1;
        } else {
            if (oldValue > 0) {
                var newVal = parseFloat(oldValue) - 1;
            } else {
                newVal = 0;
            }
        }
        button.parent().parent().find('input').val(newVal);
    });
    
})(jQuery);

  $(document).ready(function(){
    $('.owl-carousel').owlCarousel({
      loop: true,
      margin: 20,
      nav: true,
      dots: false,
      navText: ['<i class="fa fa-chevron-left text-dark"></i>', '<i class="fa fa-chevron-right text-dark"></i>'],
      responsive: {
        0: { items: 3 },
        576: { items: 5 },
        768: { items: 6 },
        992: { items: 8 }
      }
    })
  });

  
  document.addEventListener("DOMContentLoaded", function () {
    const cart = document.getElementById("sideCart");
    const toggleBtn = document.getElementById("toggleCart");
    const closeBtn = cart.querySelector(".close-btn");

    // Abre y cierra el carrito
    function toggleCart(forceClose = false) {
      if (forceClose) {
        cart.classList.remove("open");
      } else {
        cart.classList.toggle("open");
      }
    }

    // Clic en el botón del carrito (ícono)
    if (toggleBtn) {
      toggleBtn.addEventListener("click", function (e) {
        e.preventDefault();
        toggleCart();
      });
    }

    // Clic en la "X" de cerrar
    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        toggleCart(true);
      });
    }

    // Clic fuera del carrito = cerrar
    document.addEventListener("click", function (event) {
      const isCartOpen = cart.classList.contains("open");
      const clickedInsideCart = cart.contains(event.target);
      const clickedToggle = toggleBtn.contains(event.target);

      if (isCartOpen && !clickedInsideCart && !clickedToggle) {
        toggleCart(true);
      }
    });
  });
