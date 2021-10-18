
LOAD '/database/rdfloader.sql';

log_enable(2,1);

/*
ld_dir_all('/mount/data/', '*.ttl', 'http://example.com/graph');
*/

--- ld_dir('/path/to/data/', '${FILENAME}', '${GRAPH_IRI}')
ld_dir('/mount/data/', 'horse.ttl', 'http://opendata.netkeiba.com/horse#');
rdf_loader_run();
checkpoint;

ld_dir('/mount/data/', 'race.ttl', 'http://opendata.netkeiba.com/race#');
rdf_loader_run();
checkpoint;