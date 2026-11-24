// Comportamiento del formulario de evaluación 360°.
// El servidor valida todo de nuevo; esto solo hace el formulario más cómodo.
(function () {
    const empleado = document.getElementById("empleado");
    const relacion = document.getElementById("relacion");               // solo para Gestión Humana
    const relacionTexto = document.getElementById("relacion-texto");    // jefes y colaboradores
    const evaluador = document.getElementById("evaluador");
    if (!empleado) return;

    // 1. Mostrar la conducta del nivel elegido (escala BARS)
    document.querySelectorAll(".comp input[type=radio]").forEach(function (radio) {
        radio.addEventListener("change", function () {
            const texto = radio.closest(".comp").querySelector(".conducta");
            texto.innerHTML = "<b>Nivel " + radio.value + ":</b> ";
            texto.appendChild(document.createTextNode(radio.dataset.desc));
        });
    });

    // 2. Liderazgo solo aparece si el evaluado tiene personal a cargo
    function actualizarCompetencias() {
        const op = empleado.selectedOptions[0];
        const esLider = op && op.dataset.lider === "1";
        document.querySelectorAll("[data-solo-lideres]").forEach(function (fs) {
            fs.hidden = !esLider;
            fs.disabled = !esLider; // un fieldset deshabilitado no se envía
        });
        if (relacion) {
            // La opción "Colaborador a cargo" solo tiene sentido si es líder
            const colab = relacion.querySelector("option[value=colab]");
            if (colab) {
                colab.disabled = !esLider;
                if (!esLider && relacion.value === "colab") relacion.value = "par";
            }
        }
        if (relacionTexto) {
            // Jefes y colaboradores: la relación la deduce el organigrama
            relacionTexto.value = op && op.dataset.rel ? op.dataset.rel : "Selecciona a quién evalúas";
        }
    }

    // 3. Gestión Humana: proponer el nombre de quien evalúa
    function proponerEvaluador() {
        if (!relacion || !evaluador) return;
        const op = empleado.selectedOptions[0];
        if (!op || !op.value) return;
        if (relacion.value === "auto") {
            evaluador.value = op.dataset.nombre;
            evaluador.readOnly = true;
        } else {
            evaluador.readOnly = false;
            if (relacion.value === "jefe") evaluador.value = op.dataset.jefe;
            else if (evaluador.value === op.dataset.nombre || evaluador.value === op.dataset.jefe) evaluador.value = "";
        }
    }

    empleado.addEventListener("change", function () { actualizarCompetencias(); proponerEvaluador(); });
    if (relacion) {
        relacion.addEventListener("change", proponerEvaluador);
        if (relacion.value === "auto" && evaluador) evaluador.readOnly = true;
    }
    actualizarCompetencias();
})();
