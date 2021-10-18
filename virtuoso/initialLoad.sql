
LOAD '/database/rdfloader.sql';

log_enable(2,1);
ld_dir_all('/mount/data/', '*.ttl', 'http://example.com/graph');
rdf_loader_run();
checkpoint;