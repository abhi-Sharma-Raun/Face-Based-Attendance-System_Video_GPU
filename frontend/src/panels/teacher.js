const BACKEND_URL = import.meta.env.VITE_BACKEND_BASE_URL;
const ATTENDANCE_ENDPOINT = `${BACKEND_URL}/${import.meta.env.VITE_ATTENDANCE_ENDPOINT}`;
let attendanceFile = null;

export function initTeacherPanel() {
    document.getElementById('attendance-video-input')?.addEventListener('change', handleVideoUpload);
    document.getElementById('btn-run-attendance')?.addEventListener('click', runAttendanceAnalysis);
    document.getElementById('form-enroll-students')?.addEventListener('submit', handleStudentEnrollment);
    document.getElementById('form-export-attendance')?.addEventListener('submit', handleRecordExport);
}

function handleVideoUpload(event) {
    const file = event.target.files[0]; if (!file) return;
    attendanceFile = file;
    document.getElementById('uploaded-video-name').innerText = `Staged File: ${file.name}`;
    document.getElementById('uploaded-video-name').classList.remove('view-hidden');
    const preview = document.getElementById('attendance-preview');
    preview.src = URL.createObjectURL(file); preview.classList.remove('view-hidden');
    document.getElementById('btn-run-attendance').classList.remove('view-hidden');

    const resultsContainer = document.getElementById('attendance-results');
    if (resultsContainer) {
        resultsContainer.classList.add('view-hidden');
    }
    const thead = document.querySelector('#results-table thead');
    const tbody = document.querySelector('#results-table tbody');
    if (thead) thead.innerHTML = '';
    if (tbody) tbody.innerHTML = '';
}

async function runAttendanceAnalysis() {
    const className = document.getElementById('attendance-class-name').value.trim();
    if (!className || !attendanceFile) return;

    const btn = document.getElementById('btn-run-attendance');
    btn.disabled = true; btn.innerText = "⏳ Processing Video Stream Arrays...";

    const formData = new FormData();
    formData.append('class_name', className); formData.append('video', attendanceFile, attendanceFile.name);

    try {
        const res = await fetch(ATTENDANCE_ENDPOINT, { method: 'POST', body: formData });
        if (res.ok) { displayAttendanceResults(await res.json()); }
        else {             
            const errorData = await res.json(); 
            alert(`Query Failed: ${errorData.detail || 'Server encountered an error.'}`)}
    } catch { alert("Analysis failed."); }
    finally { btn.disabled = false; btn.innerText = "🚀 Execute Inference Scan"; }
}

function displayAttendanceResults(result) {
    document.getElementById('attendance-results').classList.remove('view-hidden');
    const thead = document.querySelector('#results-table thead'), tbody = document.querySelector('#results-table tbody');
    thead.innerHTML = ''; tbody.innerHTML = '';
    
    const students = result.students || []; if(!students.length) return;
    const headers = Object.keys(students[0]);

    let trHead = "<tr>"; headers.forEach(h => trHead += `<th>${h.replace('_', ' ')}</th>`);
    thead.innerHTML = trHead + "</tr>";

    students.forEach(s => {
        let trRow = "<tr>"; headers.forEach(h => trRow += `<td>${s[h] !== null ? s[h] : 'N/A'}</td>`);
        tbody.innerHTML += trRow + "</tr>";
    });
}

async function handleStudentEnrollment(e) {
    e.preventDefault();
    const class_name = document.getElementById('enroll-class-name').value.trim();
    const list = document.getElementById('enroll-student-rolls').value.split(',').map(r=>r.trim()).filter(r=>r.length);

    try {
        const res = await fetch(`${BACKEND_URL}/class/add_students`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ class_name, student_roll_list: list })
        });
        const data = await res.json();
        if (res.ok) { alert(data.message); document.getElementById('enroll-student-rolls').value = ''; }
        else {
            alert(`Enrollment Error: ${data.detail || 'Unknown error occurred.'}`);
        }
    } catch { alert("Failed mapping sequence."); }
}

async function handleRecordExport(e) {
    e.preventDefault();
    const className = document.getElementById('export-class-name').value.trim();
    const filter = document.getElementById('export-student-rolls').value.trim();
    
    let endpoint = `${BACKEND_URL}/attendance/view-attendance/by_teacher`;
    let rollList = filter ? filter.split(',').map(r => r.trim()).filter(r => r.length) : null;
    const payload = {
        class_name: className,
        students_roll_list: rollList
    };
    try {
        const res = await fetch(endpoint, {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            const blob = await res.blob();
            const a = document.createElement('a'); 
            a.href = window.URL.createObjectURL(blob);
            a.download = `records_${className}.csv`; 
            a.click();
        } else {
            const errData = await res.json();
            alert(`Export failed: ${errData.detail || "Unknown error"}`);
        }
    } catch (err) {console.error(err); alert("Export mapping issue."); }
}