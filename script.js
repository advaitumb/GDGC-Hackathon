const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('videoInput');

dropZone.onclick = () => fileInput.click();

async function handleUpload() {
    const file = fileInput.files[0];
    if(!file) return alert("Select a file first!");

    const formData = new FormData();
    formData.append('video', file);

    document.getElementById('senderLoader').style.display = 'block';
    document.getElementById('senderMsg').innerText = "Chunking and Encrypting...";

    res = await fetch('http://127.0.0.1:5000/sender_upload', { method: 'POST', body: formData });
    const data = await res.json();
    
    document.getElementById('senderLoader').style.display = 'none';
    document.getElementById('senderMsg').innerText = `Done! Created ${data.parts} encrypted segments.`;
}

async function handleAssemble() {
    document.getElementById('receiverLoader').style.display = 'block';
    document.getElementById('receiverMsg').innerText = "Stitching video back together...";

    const res = await fetch('/receiver_assemble', { method: 'POST' });
    const data = await res.json();

    document.getElementById('receiverLoader').style.display = 'none';
    document.getElementById('receiverMsg').innerText = "Success! Video joined in 'receiver_storage' folder.";
}