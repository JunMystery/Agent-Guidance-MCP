function renderComment(comment) {
    document.getElementById('comments').innerHTML += comment;
}

renderComment("<img src=x onerror=alert('XSS')>");
