/* AISCaMS - front-end helpers (vanilla JavaScript, no build step). */
(function () {
    "use strict";

    /* ------------------------------------------------------------- toast */
    function toastStack() {
        var stack = document.querySelector(".toast-stack");
        if (!stack) {
            stack = document.createElement("div");
            stack.className = "toast-stack";
            document.body.appendChild(stack);
        }
        return stack;
    }

    function toast(message, type) {
        var node = document.createElement("div");
        node.className = "toast " + (type || "info");
        node.textContent = message;
        toastStack().appendChild(node);
        window.setTimeout(function () { node.remove(); }, 5200);
    }

    /* --------------------------------------------------------- requests */
    function request(url, options) {
        var config = Object.assign({ headers: { "Content-Type": "application/json" } },
            options || {});
        return fetch(url, config).then(function (response) {
            return response.json().catch(function () { return {}; })
                .then(function (data) {
                    if (!response.ok) {
                        var message = data.message || "Request failed (" + response.status + ").";
                        var error = new Error(message);
                        error.payload = data;
                        throw error;
                    }
                    return data;
                });
        });
    }

    function postJSON(url, body) {
        return request(url, { method: "POST", body: JSON.stringify(body || {}) });
    }

    function getJSON(url) {
        return request(url, { method: "GET" });
    }

    /* ----------------------------------------------------------- helpers */
    function formValues(form) {
        var data = {};
        var multi = {};
        Array.prototype.forEach.call(form.elements, function (element) {
            if (!element.name || element.disabled) { return; }
            if (element.type === "checkbox") {
                if (element.dataset.group === "list") {
                    multi[element.name] = multi[element.name] || [];
                    if (element.checked) { multi[element.name].push(element.value); }
                } else {
                    data[element.name] = element.checked;
                }
                return;
            }
            if (element.type === "radio") {
                if (element.checked) { data[element.name] = element.value; }
                return;
            }
            data[element.name] = element.value;
        });
        Object.keys(multi).forEach(function (key) { data[key] = multi[key]; });
        return data;
    }

    function escapeHtml(value) {
        return String(value === undefined || value === null ? "" : value)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function busy(button, isBusy, busyLabel) {
        if (!button) { return; }
        if (isBusy) {
            button.dataset.label = button.textContent;
            button.textContent = busyLabel || "Working...";
            button.disabled = true;
        } else {
            button.textContent = button.dataset.label || button.textContent;
            button.disabled = false;
        }
    }

    /* -------------------------------------------- generic action buttons */
    /* Any element with data-action="post" posts to data-url and reloads.   */
    document.addEventListener("click", function (event) {
        var trigger = event.target.closest("[data-action='post']");
        if (!trigger) { return; }
        event.preventDefault();
        if (trigger.dataset.confirm && !window.confirm(trigger.dataset.confirm)) { return; }
        var body = {};
        if (trigger.dataset.payload) {
            try { body = JSON.parse(trigger.dataset.payload); } catch (err) { body = {}; }
        }
        if (trigger.dataset.field) {
            var input = document.querySelector(trigger.dataset.field);
            if (input) { body[trigger.dataset.key || "value"] = input.value; }
        }
        busy(trigger, true);
        postJSON(trigger.dataset.url, body).then(function (data) {
            toast(data.message || "Done.", "success");
            if (trigger.dataset.reload !== "false") {
                window.setTimeout(function () { window.location.reload(); }, 700);
            } else {
                busy(trigger, false);
            }
        }).catch(function (error) {
            toast(error.message, "error");
            busy(trigger, false);
        });
    });

    /* Generic JSON forms: data-json-form with data-url. */
    document.addEventListener("submit", function (event) {
        var form = event.target;
        if (!form.matches("[data-json-form]")) { return; }
        event.preventDefault();
        var button = form.querySelector("[type='submit']");
        busy(button, true, "Submitting...");
        postJSON(form.dataset.url, formValues(form)).then(function (data) {
            toast(data.message || "Saved.", "success");
            if (form.dataset.reload !== "false") {
                window.setTimeout(function () { window.location.reload(); }, 900);
            } else {
                busy(button, false);
                form.reset();
            }
        }).catch(function (error) {
            toast(error.message, "error");
            busy(button, false);
        });
    });

    window.AISCAMS = {
        toast: toast,
        postJSON: postJSON,
        getJSON: getJSON,
        formValues: formValues,
        escapeHtml: escapeHtml,
        busy: busy
    };
}());
