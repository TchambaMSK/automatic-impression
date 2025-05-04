document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form");
    const loader = document.querySelector(".loader-overlay");
    const pdfPreviewContainer = document.getElementById("pdf-preview");
    const fileInput = document.querySelector("input[type='file']");
    const prevButton = document.getElementById("prev-page");
    const nextButton = document.getElementById("next-page");
    let pdfDoc = null;
    let currentPage = 1;
  
    // Afficher l'aperçu du PDF
    fileInput.addEventListener("change", function (e) {
      const file = e.target.files[0];
  
      if (file && file.type === "application/pdf") {
        const fileReader = new FileReader();
        
        fileReader.onload = function () {
          const pdfData = new Uint8Array(fileReader.result);
  
          // Initialiser le PDF.js
          pdfjsLib.getDocument(pdfData).promise.then(function (doc) {
            pdfDoc = doc;
            currentPage = 1;
            renderPage(currentPage);
            pdfPreviewContainer.style.display = "block";
          });
        };
  
        fileReader.readAsArrayBuffer(file);
      } else {
        alert("Veuillez sélectionner un fichier PDF.");
      }
    });
  
    // Rendu de la page PDF
    function renderPage(pageNum) {
      pdfDoc.getPage(pageNum).then(function (page) {
        const scale = 1.5;
        const viewport = page.getViewport({ scale: scale });
  
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        canvas.height = viewport.height;
        canvas.width = viewport.width;
  
        pdfPreviewContainer.innerHTML = ""; // Réinitialiser le conteneur
        pdfPreviewContainer.appendChild(canvas);
  
        const renderContext = {
          canvasContext: ctx,
          viewport: viewport,
        };
        page.render(renderContext);
      });
    }
  
    // Boutons de navigation
    prevButton.addEventListener("click", function () {
      if (currentPage > 1) {
        currentPage--;
        renderPage(currentPage);
      }
    });
  
    nextButton.addEventListener("click", function () {
      if (currentPage < pdfDoc.numPages) {
        currentPage++;
        renderPage(currentPage);
      }
    });
  
    form.addEventListener("submit", (e) => {
      const confirmSend = confirm("Voulez-vous vraiment envoyer ce document à imprimer ?");
      if (!confirmSend) {
        e.preventDefault();
      } else {
        loader.style.display = "flex";
      }
    });
  });
  