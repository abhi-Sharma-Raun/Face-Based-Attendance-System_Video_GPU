const BACKEND_URL = import.meta.env.VITE_BACKEND_BASE_URL;

export function initAdminPanel() {
    document.getElementById('form-add-teacher')?.addEventListener('submit', handleAddTeacher);
    document.getElementById('form-add-class')?.addEventListener('submit', handleAddClass);
    document.getElementById('tab-view-classes')?.addEventListener('click', fetchAndRenderClasses);
    document.getElementById('btn-refresh-classes')?.addEventListener('click', fetchAndRenderClasses);
}

async function handleAddTeacher(e) {
    e.preventDefault();
    const name = document.getElementById('teacher-name').value.trim();
    const email = document.getElementById('teacher-email').value.trim();
    const department = document.getElementById('teacher-dept').value.trim();

    try {
        const res = await fetch(`${BACKEND_URL}/teachers/add_teacher`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, department })
        });
        if (res.ok) {
            const data = await res.json();
            alert(`Success: ${data.message}`);
            e.target.reset();
        } else { alert("Failed to add faculty profile mapping."); }
    } catch (err) { alert("Error network payload broadcast: " + err.message); }
}

async function handleAddClass(e) {
    e.preventDefault();
    const payload = {
        class_name: document.getElementById('class-name').value.trim(),
        batch_start_year: parseInt(document.getElementById('batch-start-year').value),
        curr_year: parseInt(document.getElementById('class-curr-year').value),
        course_id: document.getElementById('class-course-id').value.trim(),
        department: document.getElementById('class-dept').value.trim(),
        branch: document.getElementById('class-branch').value.trim()
    };

    try {
        const res = await fetch(`${BACKEND_URL}/class/add_class`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const data = await res.json();
            alert(`Success: ${data.message}`);
            e.target.reset();
        } else { alert("Conflict or issue initializing system class parameters."); }
    } catch (err) { alert("Error writing class structure parameters: " + err.message); }
}


async function fetchAndRenderClasses() {
    const tableBody = document.getElementById('classes-table-body');
    if (!tableBody) return;

    try {
        const res = await fetch(`${BACKEND_URL}/class/view_all_classes`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });

        if (res.status === 404) {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-warning">No classes have been initialized yet.</td></tr>`;
            return;
        }

        if (!res.ok) throw new Error("Server returned an error status.");

        const data = await res.json();
        const classes = data.all_classes || [];

        if (classes.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No classes active.</td></tr>`;
            return;
        }

        tableBody.innerHTML = classes.map(c => `
            <tr>
                <td class="font-weight-bold">${escapeHtml(c.class_name)}</td>
                <td><code class="text-dark">${escapeHtml(c.course_id)}</code></td>
                <td>${escapeHtml(c.department_id || c.department || 'N/A')}</td>
                <td>${c.batch_start_year}</td>
                <td><span class="badge badge-secondary">Year ${c.curr_year}</span></td>
            </tr>
        `).join('');

    } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Failed to sync infrastructure: ${err.message}</td></tr>`;
    }
}

// Simple security helper function to sanitize user string rendering
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}