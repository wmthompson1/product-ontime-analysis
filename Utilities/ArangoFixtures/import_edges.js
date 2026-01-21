var fs = require('fs');
try {
    var e = JSON.parse(fs.readFileSync('/workspace/Utilities/ArangoFixtures/edges.json', 'utf8'));
    if (!db._collection('manufacturing_semantic_layer_edges')) {
        db._createEdgeCollection('manufacturing_semantic_layer_edges');
    }
    e.forEach(function (d) { db.manufacturing_semantic_layer_edges.save(d); });
    print('imported edges: ' + e.length);
} catch (err) {
    print('ERROR importing edges:', err.toString());
}
