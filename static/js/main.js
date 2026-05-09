// Flash Messages Auto Dismiss
setTimeout(() => {
    document.querySelectorAll('.flash').forEach(el => {
        el.style.transition = 'opacity 0.5s';
        el.style.opacity = '0';
        setTimeout(() => el.remove(), 600);
    });
}, 4000);

// Dynamic Subject Fields
let subjectCount = 0;

function addSubject() {
    subjectCount++;

    const container = document.getElementById('subjectsContainer');

    const div = document.createElement('div');
    div.className = 'subject-row';
    div.innerHTML = `
        <div>
            <label>Subject Name</label>
            <input type="text" name="subject_name_${subjectCount}" placeholder="e.g. Operating System" required>
        </div>
        <div>
            <label>Obtained Marks</label>
            <input type="number" step="any" name="obtained_${subjectCount}" placeholder="85" required>
        </div>
        <div>
            <label>Total Marks</label>
            <input type="number" step="any" name="total_${subjectCount}" value="100" required>
        </div>
        <div>
            <button type="button" class="remove-btn" onclick="this.closest('.subject-row').remove()">✕</button>
        </div>
    `;

    container.appendChild(div);
}

// Add first subject automatically when page loads
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('subjectsContainer')) {
        addSubject();   // Add first subject by default
    }
});