document.addEventListener('DOMContentLoaded', () => {
    // Status update handler
    document.querySelectorAll('.status-select').forEach(select => {
        select.addEventListener('change', async (e) => {
            const row = e.target.closest('tr');
            const filename = row.dataset.filename;
            const newStatus = e.target.value;
            
            try {
                const response = await fetch('/admin/queue/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        filename: filename,
                        status: newStatus
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const statusBadge = row.querySelector('.status-badge');
                    statusBadge.className = `status-badge ${newStatus}`;
                    statusBadge.textContent = newStatus.charAt(0).toUpperCase() + newStatus.slice(1);
                    
                    // Show success feedback
                    showToast('Status updated successfully');
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('Failed to update status', 'error');
            }
        });
    });
    
    // Notes button handler
    document.querySelectorAll('.notes-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const filename = e.target.dataset.filename;
            const notes = prompt('Enter notes for this print job:');
            
            if (notes !== null) {
                try {
                    const response = await fetch('/admin/queue/update', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            filename: filename,
                            notes: notes
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        showToast('Notes added successfully');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showToast('Failed to add notes', 'error');
                }
            }
        });
    });
    
    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', () => {
        window.location.reload();
    });
    
    // Auto-refresh every 60 seconds
    setInterval(() => {
        window.location.reload();
    }, 60000);
    
    // Toast notification function
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }
});