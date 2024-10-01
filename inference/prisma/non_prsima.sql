CREATE TABLE memory_search_vector (
    memId TEXT,
    chunkId TEXT,
    search_vector tsvector,
    PRIMARY KEY (memId, chunkId)
);

CREATE INDEX idx_memory_search_vector ON memory_search_vector USING GIN (search_vector);