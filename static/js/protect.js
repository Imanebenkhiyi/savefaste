(function () {
    // اسمح بالنطاق الفعلي + localhost أثناء التطوير
    const allowedDomains = ["savefaste.com", "www.savefaste.com", "localhost", "127.0.0.1"];
    const currentHost = window.location.hostname;

    if (!allowedDomains.includes(currentHost)) {
        document.body.innerHTML = "<h2>Unauthorized domain!</h2>";
        console.error("Script blocked: invalid domain", currentHost);
        return; // بدل throw لمنع الصفحة البيضاء
    }

    // تعطيل الزر الأيمن للفأرة
    document.addEventListener("contextmenu", e => e.preventDefault());

    // تعطيل F12 / Inspect
    document.onkeydown = e => {
        if (
            e.keyCode === 123 ||
            (e.ctrlKey && e.shiftKey && ["I", "C", "J"].includes(e.key.toUpperCase())) ||
            (e.ctrlKey && e.key.toUpperCase() === "U")
        ) {
            return false;
        }
    };

})();
