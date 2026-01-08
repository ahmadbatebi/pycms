(function() {
    const jumpBtn = document.getElementById('jumpToTop');
    if (!jumpBtn) {
        return;
    }

    let scrollTimeout;

    function toggleButton() {
        if (window.scrollY > 300) {
            jumpBtn.classList.add('visible');
        } else {
            jumpBtn.classList.remove('visible');
        }
    }

    window.addEventListener('scroll', function() {
        if (scrollTimeout) {
            window.cancelAnimationFrame(scrollTimeout);
        }
        scrollTimeout = window.requestAnimationFrame(toggleButton);
    }, { passive: true });

    jumpBtn.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });

    toggleButton();
})();
