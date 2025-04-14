// app/static/js/script.js
document.addEventListener('DOMContentLoaded', function() {
    // Handle tab navigation
    const tabs = document.querySelectorAll('.tab-button');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Hide all tab panes
            const panes = document.querySelectorAll('.tab-pane');
            panes.forEach(pane => pane.classList.remove('active'));
            
            // Show the selected pane
            const targetId = this.getAttribute('data-tab');
            document.getElementById(targetId).classList.add('active');
        });
    });

    // Fix for language bar fills
    document.querySelectorAll('.language-bar-fill').forEach(bar => {
        if (bar.style.width === '') {
            // Apply a default width if style is not set
            const defaultWidth = '10%';
            bar.style.width = defaultWidth;
        }
    });
});