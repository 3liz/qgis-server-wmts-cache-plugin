

async function api_get( uri ) {

    if (!uri.startsWith("http")) {
        uri = `/wmtscache/${uri}`;
    }

    let response = await fetch(uri, {
        credentials: 'same-origin',
        method: 'GET',
    });
    if (! response.ok) {
        let msg = await response.text();
        alert("Server returned "+ response.status + "\n" + msg);
        return null;
    }
    return await response.json();
}


async function api_post( uri, data ) {
    let response = await fetch(`/wmtscache/${uri}`, {
        credentials: 'same-origin',
        method: 'POST',
        body: JSON.stringify(data)
    });
    if (! response.ok) {
        let msg = await response.text();
        alert("Server returned "+ response.status + "\n" + msg);
        return null;
    }
    return await response.json();
}


async function api_put( uri, data ) {
    let response = await fetch(`/wmtscache/${uri}`, {
        credentials: 'same-origin',
        method: 'PUT',
        body: JSON.stringify(data)
    });
    if (! response.ok) {
        let msg = await response.text();
        alert("Server returned "+ response.status + "\n" + msg);
        return null;
    }
    return await response.json();
}

async function api_delete( uri ) {
    let response = await fetch(`/wmtscache/${uri}`, {
        credentials: 'same-origin',
        method: 'DELETE',
    });
    if (! response.ok) {
        let msg = await response.text();
        alert("Server returned "+ response.status + "\n" + msg);
        return null;
    }
    return await response.json();
}

/*
 * Helpers
 */

function set_options(select, options, clear = true) {
    if (clear) {
        const length = select.length
        for (let i=0; i<length; i++) {
            select.remove(0);
        }
    }
    for (const [text, value] of options) {
        select.options[select.options.length] = new Option(text,value);
    }
}

function get_options_checked(selector) {
    return document.querySelectorAll(`${selector} option:checked`);
}

function get_options_values(selector) {
    let selected = get_options_checked(selector);
    return Array.from(selected).map(el => el.value);
}

