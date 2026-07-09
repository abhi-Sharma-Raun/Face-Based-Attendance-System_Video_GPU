const BACKEND_URL = import.meta.env.VITE_BACKEND_BASE_URL;

export function initAdminPanel() {
    document.getElementById('form-add-teacher')?.addEventListener('submit', handleAddTeacher);
    document.getElementById('form-add-class')?.addEventListener('submit', handleAddClass);
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
        batch_start_year: parseInt(document.getElementById('class-start-year').value),
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