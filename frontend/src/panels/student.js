import { FilesetResolver, FaceLandmarker } from '@mediapipe/tasks-vision';

const BACKEND_URL = import.meta.env.VITE_BACKEND_BASE_URL;
const REGISTRATION_ENDPOINT = `${BACKEND_URL}/${import.meta.env.VITE_REGISTRATION_ENDPOINT}`;

let faceLandmarker = null, webcamStream = null, animationFrameId = null;
let selectedFrames = {}, scanComplete = false;

export async function initStudentPanel() {
    document.getElementById('btn-start-scan')?.addEventListener('click', startVerificationScan);
    document.getElementById('btn-retake-scan')?.addEventListener('click', resetScanState);
    document.getElementById('btn-submit-registration')?.addEventListener('click', submitRegistration);
    document.getElementById('form-query-attendance')?.addEventListener('submit', handleAttendanceQuery);
    await initializeFaceLandmarker();
}

async function initializeFaceLandmarker() {
    try {
        const vision = await FilesetResolver.forVisionTasks("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm");
        faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
            baseOptions: { modelAssetPath: `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`, delegate: "CPU" },
            outputFaceBlendshapes: false, outputFacialTransformationMatrixes: true, runningMode: "VIDEO", numFaces: 1
        });
    } catch (error) { console.error("WASM model fault:", error); }
}

async function startVerificationScan() {
    const name = document.getElementById('reg-name').value.trim();
    const rollNum = document.getElementById('reg-roll').value.trim();
    const email = document.getElementById('reg-email').value.trim();

    if (!name || !rollNum || !email) { alert("Please supply all input fields."); return; }
    if (!faceLandmarker) { alert("Engine still downloading. Standby..."); return; }

    selectedFrames = {}; scanComplete = false;
    document.getElementById('capture-hud').innerText = "Captured: []";
    document.getElementById('btn-start-scan').classList.add('view-hidden');
    document.getElementById('scan-active-status').classList.remove('view-hidden');
    document.getElementById('video-wrapper').classList.remove('view-hidden');

    const video = document.getElementById('webcam');
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" }, audio: false });
        video.srcObject = webcamStream;
        video.addEventListener('loadeddata', () => { video.play(); animationFrameId = requestAnimationFrame(renderTrackingLoop); });
    } catch { resetScanState(); }
}

async function renderTrackingLoop() {
    const video = document.getElementById('webcam'), canvas = document.getElementById('canvas-overlay');
    if (!video || !canvas) return;
    const ctx = canvas.getContext('2d');

    if (!video.videoWidth || video.paused || video.ended) { animationFrameId = requestAnimationFrame(renderTrackingLoop); return; }
    if (canvas.width !== video.videoWidth) { canvas.width = video.videoWidth; canvas.height = video.videoHeight; }
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const result = faceLandmarker.detectForVideo(video, Date.now());
    if (result?.facialTransformationMatrixes?.[0]?.data) {
        const matrixData = result.facialTransformationMatrixes[0].data;
        const yawDegrees = Math.atan2(-matrixData[8], Math.sqrt(Math.pow(matrixData[9], 2) + Math.pow(matrixData[10], 2))) * (180 / Math.PI);
        let pose = null;

        if (yawDegrees >= -10 && yawDegrees <= 10 && !selectedFrames["front"]) pose = "front";
        else if (yawDegrees > 30 && !selectedFrames["right"]) pose = "right";
        else if (yawDegrees < -30 && !selectedFrames["left"]) pose = "left";

        if (pose) {
            selectedFrames[pose] = await captureCanvasFrameBlob(video);
            document.getElementById('capture-hud').innerText = `Captured: [${Object.keys(selectedFrames).join(', ')}]`;
        }
    }

    if (Object.keys(selectedFrames).length === 3) {
        scanComplete = true; stopWebcamStream();
        document.getElementById('video-wrapper').classList.add('view-hidden');
        document.getElementById('scan-active-status').classList.add('view-hidden');
        document.getElementById('scan-success-status').classList.remove('view-hidden');
        return;
    }
    animationFrameId = requestAnimationFrame(renderTrackingLoop);
}

function captureCanvasFrameBlob(videoElement) {
    return new Promise((r) => {
        const c = document.createElement('canvas'); c.width = videoElement.videoWidth; c.height = videoElement.videoHeight;
        c.getContext('2d').drawImage(videoElement, 0, 0, c.width, c.height);
        c.toBlob((b) => r(b), 'image/jpeg', 0.95);
    });
}

function stopWebcamStream() {
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    webcamStream?.getTracks().forEach(t => t.stop());
}

export function resetScanState() {
    stopWebcamStream(); scanComplete = false; selectedFrames = {};
    document.getElementById('video-wrapper').classList.add('view-hidden');
    document.getElementById('scan-success-status').classList.add('view-hidden');
    document.getElementById('btn-start-scan').classList.remove('view-hidden');
}

async function submitRegistration() {
    const name = document.getElementById('reg-name').value.trim();
    const rollNum = document.getElementById('reg-roll').value.trim();
    const email = document.getElementById('reg-email').value.trim();

    if (!scanComplete) { alert("Complete the automated webcam sweep first."); return; }
    const formData = new FormData();
    formData.append('name', name); formData.append('email', email); formData.append('roll_num', rollNum);
    formData.append('files', selectedFrames['front'], 'front.jpg');
    formData.append('files', selectedFrames['left'], 'left.jpg');
    formData.append('files', selectedFrames['right'], 'right.jpg');

    try {
        const res = await fetch(REGISTRATION_ENDPOINT, { method: 'POST', body: formData });
        if (res.ok) { alert("Registration complete!"); resetScanState(); window.location.href = "index.html"; }
        else {
            const errorData = await res.json();
            alert(`Registration Failed: ${errorData.detail || 'Unknown Server Error'}`);
        }
        
    } catch (err) { alert(`Network error encountered: ${err.message}`); }
    finally { submitBtn.disabled = false; submitBtn.innerHTML = originalBtnText; }
}

async function handleAttendanceQuery(e) {
    e.preventDefault();
    const roll = document.getElementById('query-roll').value.trim();
    const cls = document.getElementById('query-class').value.trim();
    const start = document.getElementById('query-start-date').value;
    const end = document.getElementById('query-end-date').value;

    let url = `${BACKEND_URL}/attendance/view-attendance/by_student/${encodeURIComponent(roll)}/${encodeURIComponent(cls)}`;
    const params = [];
    if (start) params.push(`start_date=${start}`);
    if (end) params.push(`end_date=${end}`);
    if (params.length) url += `?${params.join('&')}`;

    try {
        const res = await fetch(url);
        if (res.ok) {
            const data = await res.json();
            const tbody = document.querySelector('#student-records-table tbody');
            tbody.innerHTML = '';
            document.getElementById('student-query-results').classList.remove('view-hidden');
            if(!data.present_dates.length) { tbody.innerHTML = "<tr><td colspan='2'>No entries found.</td></tr>"; return; }
            data.present_dates.forEach(d => {
                tbody.innerHTML += `<tr><td><strong>${d}</strong></td><td><span class='badge badge-success'>✔ Present</span></td></tr>`;
            });
        }
        else{
            const errorData = await res.json();
            alert(`Query Failed: ${errorData.detail || 'Server encountered an error.'}`);
        }
    } catch { alert("Query failed."); }
}