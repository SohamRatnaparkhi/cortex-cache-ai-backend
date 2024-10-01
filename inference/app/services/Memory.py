from app.prisma.prisma import full_text_search
from app.utils.Pinecone_query import pinecone_query
from app.utils.Preprocessor import prepare_fulltext_query


def get_semantic_search_results(original_query, refined_query, metadata, top_k=15):
    refined_query_semantic_res = pinecone_query(refined_query, metadata, top_k)
    original_query_semantic_res = pinecone_query(
        original_query, metadata, top_k)
    print("Semantic search results")
    print(
        f"Lenght of original query results: {len(original_query_semantic_res)}")
    print(
        f"Lenght of refined query results: {len(refined_query_semantic_res)}")
    return original_query_semantic_res, refined_query_semantic_res


async def get_full_text_search_results(original_query, refined_query, metadata, top_k=15):

    original_query_full_text_res = await full_text_search(
        prepare_fulltext_query(original_query), metadata, top_k)
    refined_query_full_text_res = await full_text_search(
        prepare_fulltext_query(refined_query), metadata, top_k)
    return original_query_full_text_res, refined_query_full_text_res


def reciprocal_rank_fusion(result_lists, k=60):
    print(f"Length of result lists: {len(result_lists)}")
    fused_scores = {}
    for results in result_lists:
        for rank, res in enumerate(results):
            memId = res["memId"]  # Ensure res is a dictionary
            chunkId = res["chunkId"]
            score = res["score"]
            doc_key = (memId, chunkId)
            if doc_key not in fused_scores:
                fused_scores[doc_key] = 0
            # Ensure score is a float before multiplication
            if isinstance(score, (int, float)):
                fused_scores[doc_key] += (1 / (rank + k)) * score
            else:
                print(f"Warning: Score for {doc_key} is not numeric: {score}")

    sorted_results = sorted(fused_scores.items(),
                            key=lambda x: x[1], reverse=True)
    return [(memId, chunkId, score) for (memId, chunkId), score in sorted_results]


def apply_relative_threshold(fused_results, relative_threshold=0.6):
    if not fused_results:
        return []
    top_score = fused_results[0][2]  # top score
    threshold = top_score * relative_threshold
    return [{"memId": memId, "chunkId": chunkId, "score": score} for memId, chunkId, score in fused_results if score >= threshold]


async def get_final_results_from_memory(original_query, refined_query, metadata, top_k=15, max_results=15, relative_threshold=0.6):
    original_query_semantic_res, refined_query_semantic_res = get_semantic_search_results(
        original_query, refined_query, metadata, top_k)
    original_query_full_text_res, refined_query_full_text_res = await get_full_text_search_results(
        original_query, refined_query, metadata, top_k)

    fused_list = []
    if not len(original_query_semantic_res) == 0:
        fused_list.append(original_query_semantic_res)

    if not len(refined_query_semantic_res) == 0:
        fused_list.append(refined_query_semantic_res)

    if not len(original_query_full_text_res) == 0:
        fused_list.append(original_query_full_text_res)

    if not len(refined_query_full_text_res) == 0:
        fused_list.append(refined_query_full_text_res)

    fused_results = reciprocal_rank_fusion(fused_list, top_k)

    print(fused_results[0])
    print("Final results received. Now dance")
    return apply_relative_threshold(fused_results, relative_threshold)[: max_results]


# def format_list_obj
