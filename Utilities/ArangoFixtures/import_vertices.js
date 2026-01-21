var fs = require('fs');
try {
    var v = JSON.parse(fs.readFileSync('/workspace/Utilities/ArangoFixtures/vertices.json', 'utf8'));
    if (!db._collection('manufacturing_semantic_layer_vertices')) {
        db._createDocumentCollection('manufacturing_semantic_layer_vertices');
    }
    v.forEach(function (d) { db.manufacturing_semantic_layer_vertices.save(d); });
    print('imported vertices: ' + v.length);
} catch (e) {
    print('ERROR importing vertices:', e.toString());
}
