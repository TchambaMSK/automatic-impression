document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("form");
  const loader = document.querySelector(".loader-overlay");
  const pdfPreviewContainer = document.getElementById("pdf-preview");
  const fileInput = document.querySelector("input[type='file']");
  const prevButton = document.getElementById("prev-page");
  const nextButton = document.getElementById("next-page");
  const currentPageSpan = document.getElementById("current-page");
  const totalPagesSpan = document.getElementById("total-pages");
  
  let pdfDoc = null;
  let currentPage = 1;
  let pdfRenderTask = null;

  // PDF Preview Handler
  fileInput.addEventListener("change", function(e) {
    const file = e.target.files[0];
    
    if (file && file.type === "application/pdf") {
      if (pdfRenderTask) pdfRenderTask.cancel();
      
      const fileReader = new FileReader();
      
      fileReader.onload = function() {
        pdfPreviewContainer.innerHTML = '<p class="loading-text">Chargement du PDF...</p>';
        pdfPreviewContainer.style.display = "block";
        
        const pdfData = new Uint8Array(fileReader.result);
        
        pdfjsLib.getDocument(pdfData).promise.then(function(doc) {
          pdfDoc = doc;
          currentPage = 1;
          updatePageCounter();
          renderPage(currentPage);
        }).catch(function(error) {
          console.error("PDF error:", error);
          pdfPreviewContainer.innerHTML = '<p class="error-text">Erreur de chargement du PDF</p>';
        });
      };
      
      fileReader.readAsArrayBuffer(file);
    } else {
      alert("Veuillez sélectionner un fichier PDF valide.");
      fileInput.value = "";
    }
  });

  // Render PDF Page
  function renderPage(pageNum) {
    if (!pdfDoc) return;
    
    if (pdfRenderTask) pdfRenderTask.cancel();
    
    pdfPreviewContainer.innerHTML = '<p class="loading-text">Chargement de la page...</p>';
    
    pdfDoc.getPage(pageNum).then(function(page) {
      const containerWidth = pdfPreviewContainer.clientWidth - 40;
      const scale = containerWidth / page.getViewport({ scale: 1 }).width;
      const viewport = page.getViewport({ scale: scale });
      
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      
      pdfPreviewContainer.innerHTML = "";
      pdfPreviewContainer.appendChild(canvas);
      
      pdfRenderTask = page.render({
        canvasContext: context,
        viewport: viewport
      });
      
      updatePageCounter();
    }).catch(function(error) {
      console.error("Page render error:", error);
      pdfPreviewContainer.innerHTML = '<p class="error-text">Erreur de rendu de la page</p>';
    });
  }

  // Update Page Counter
  function updatePageCounter() {
    currentPageSpan.textContent = currentPage;
    totalPagesSpan.textContent = pdfDoc ? pdfDoc.numPages : 1;
    prevButton.disabled = currentPage <= 1;
    nextButton.disabled = currentPage >= pdfDoc.numPages;
  }

  // Navigation Buttons
  prevButton.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      renderPage(currentPage);
    }
  });

  nextButton.addEventListener("click", () => {
    if (pdfDoc && currentPage < pdfDoc.numPages) {
      currentPage++;
      renderPage(currentPage);
    }
  });

  // Form Submission
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const confirmSend = confirm("Voulez-vous vraiment envoyer ce document à imprimer ?");
    if (!confirmSend) return;
    
    try {
      loader.style.display = "flex";
      const formData = new FormData(form);
      
      const response = await fetch("/upload", {
        method: "POST",
        body: formData
      });
      
      if (!response.ok) throw new Error("Erreur serveur");
      
      alert("Document envoyé avec succès !");
      form.reset();
      pdfPreviewContainer.style.display = "none";
    } catch (error) {
      console.error("Upload error:", error);
      alert("Erreur lors de l'envoi du document");
    } finally {
      loader.style.display = "none";
    }
  });
});