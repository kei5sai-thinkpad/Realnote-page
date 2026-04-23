html = """
<!DOCTYPE html>
<html>
<body>
<input id="room" placeholder="room">
<button onclick="joinRoom()">join</button>
<br><br>
<textarea id="note" style="width:100%;height:300px;"></textarea>

<script>
let ws;

function joinRoom() {
    const room = document.getElementById("room").value;
    const note = document.getElementById("note");

    ws = new WebSocket(
        (location.protocol === "https:" ? "wss://" : "ws://")
        + location.host + "/ws/" + room
    );

    ws.onmessage = (event) => {
        note.value = event.data;
    };

    note.oninput = () => {
        ws.send(note.value);
    };
}
</script>
</body>
</html>
"""
