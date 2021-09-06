
/*
 * Populate select input with
 * projects
 */


async function update_doc_infos(id) {
    const data = await api_get(`collections/${id}/docs`);
    if (data == null) {
        return null;
    }
    document.getElementById("docs-info-label").setAttribute('data-value', data.documents);
    return data;
}

async function update_layer_infos(id) {
    const data = await api_get(`collections/${id}`);
    if (data == null) {
        return null;
    }
    document.getElementById("layers-info-label").setAttribute('data-value', data.layers.length);
    const layers = document.getElementById('layer-input');
    set_options(layers, Array.from(data.layers, l => [l.id, l.id])); 
    return data;
}

function clear_infos() {
    const layers = document.getElementById('layer-input');
    set_options(layers, []); 
    document.getElementById("data-pane").setAttribute("status", "notset");
}

async function update_project_infos(id) {
    document.getElementById("remove-layer-btn").disabled=true;
    const data = await update_layer_infos(id);
    if (data == null) {
        document.getElementById("data-pane").setAttribute("status", "notset");
        return;
    }
    await update_doc_infos(id);
    document.getElementById("project-label").textContent = data.project;
    document.getElementById("data-pane").setAttribute("status", "set");
}

function refresh_infos() {
    const id = document.getElementById('project-input').value;
    update_project_infos(id);
}

function on_project_changed(select) {
    update_project_infos(select.value);
}


function on_layers_changed(select) {
    const selected = get_options_checked('#layer-input');
    document.getElementById("remove-layer-btn").disabled=(selected.length == 0);
}

async function remove_selected_tiles() {
    const id = document.getElementById('project-input').value;
    const values = get_options_values('#layer-input');
    if (window.confirm(`Remove tiles from selected layers for project ${id} ?`)) {
        for (const layerid of values) {
            await api_delete(`collections/${id}/layers/${layerid}`);
            update_layer_infos(id);
        }
    }
}

async function remove_all_tiles() {
    const id = document.getElementById('project-input').value;
    if (window.confirm(`Remove all documents for project ${id} ?`)) {
        await api_delete(`collections/${id}/layers`);
        update_layer_infos(id);
    }
}

async function remove_all_documents() {
    const id = document.getElementById('project-input').value;
    if (window.confirm(`Remove all documents for project ${id} ?`)) {
        await api_delete(`collections/${id}/docs`);
        update_doc_infos(id);
    }
}


async function remove_project() {
    const id = document.getElementById('project-input').value;
    if (window.confirm(`Remove all documents and tiles for project ${id} ?`)) {
        await api_delete(`collections/${id}`);
        populate_projects();
    }
}



async function populate_projects() {
    clear_infos();
    let select = document.getElementById('project-input')
    set_options(select, []);
    // Repopulate selection
    const result = await api_get('collections');
    if (result != null) {
       set_options(select, Array.from(result.collections, p => [p.project, p.id])); 
    }
}



function initialize() {
    populate_projects();
}
