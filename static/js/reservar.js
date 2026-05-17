document.addEventListener('DOMContentLoaded', function() {
    
    var radios = document.querySelectorAll('.duracion-radio');
    
    radios.forEach(function(radio) {
        radio.addEventListener('change', function() {
            // Resetear todos
            document.querySelectorAll('.duracion-card').forEach(function(card) {
                card.style.borderColor = '#eef0f5';
                card.style.background = '#f8f9fb';
            });
            
            // Activar seleccionado
            var card = this.nextElementSibling;
            card.style.borderColor = '#1a237e';
            card.style.background = '#eef1ff';
        });
    });
    
});