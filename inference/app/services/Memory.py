from app.prisma.prisma import full_text_search
from app.utils.Pinecone_query import pinecone_query
from app.utils.Preprocessor import prepare_fulltext_query


def get_semantic_search_results(original_query, refined_query, metadata, top_k=15, absolute_threshold=0.1):
    refined_query_semantic_res = pinecone_query(refined_query, metadata, top_k)
    original_query_semantic_res = pinecone_query(
        original_query, metadata, top_k)
    print("Semantic search results")
    print(
        f"Lenght of original query results: {len(original_query_semantic_res)}")
    print(
        f"Lenght of refined query results: {len(refined_query_semantic_res)}")

    filtered_refined_query_semantic_res = [
        res for res in refined_query_semantic_res if res["score"] >= absolute_threshold]

    filtered_original_query_semantic_res = [
        res for res in original_query_semantic_res if res["score"] >= absolute_threshold]

    return filtered_original_query_semantic_res, filtered_refined_query_semantic_res


async def get_full_text_search_results(original_query, refined_query, metadata, top_k=15):

    original_query_full_text_res = await full_text_search(
        prepare_fulltext_query(original_query), metadata, top_k)
    refined_query_full_text_res = await full_text_search(
        prepare_fulltext_query(refined_query), metadata, top_k)
    return original_query_full_text_res, refined_query_full_text_res


def reciprocal_rank_fusion(result_lists, k=100):
    print(f"Length of result lists: {len(result_lists)}")

    semantic_weight = 0.7
    full_text_weight = 0.3
    # Before ranking scores
    print("Before ranking scores")
    fused_scores = {}
    for results in result_lists:
        for rank, res in enumerate(results):
            memId = res["memId"]  # Ensure res is a dictionary
            chunkId = res["chunkId"]
            score = res["score"]
            source = res["source"]

            weight = semantic_weight if source == "semantic" else full_text_weight

            print(f"MemId: {memId}, ChunkId: {chunkId}, Score: {score}")

            doc_key = (memId, chunkId)
            if doc_key not in fused_scores:
                fused_scores[doc_key] = 0
            # Ensure score is a float before multiplication
            if isinstance(score, (int, float)):
                fused_scores[doc_key] += (weight /
                                          (rank + k)) * scale_score(score)
            else:
                print(f"Warning: Score for {doc_key} is not numeric: {score}")

    sorted_results = sorted(fused_scores.items(),
                            key=lambda x: x[1], reverse=True)
    return [(memId, chunkId, score) for (memId, chunkId), score in sorted_results]


def apply_relative_threshold(fused_results, relative_threshold=0.6):
    if not fused_results:
        return []
    top_score = max(fused_results[0][2], relative_threshold/2)  # top score
    threshold = top_score * relative_threshold
    print(f"Threshold: {threshold}")
    print("Scores")
    for memId, chunkId, score in fused_results:
        print(f"MemId: {memId}, ChunkId: {chunkId}, Score: {score}")
    return [{"memId": memId, "chunkId": chunkId, "score": score} for memId, chunkId, score in fused_results if score >= threshold]


async def get_final_results_from_memory(original_query, refined_query, metadata, top_k=15, max_results=15, relative_threshold=0.6):
    original_query_semantic_res, refined_query_semantic_res = get_semantic_search_results(
        original_query, refined_query, metadata, top_k)
    original_query_full_text_res, refined_query_full_text_res = await get_full_text_search_results(
        original_query, refined_query, metadata, top_k)

    print("Length of original + semantic = ", len(original_query_semantic_res))
    print("Length of refined + semantic = ", len(refined_query_semantic_res))
    print("Length of original + full_text = ",
          len(original_query_full_text_res))
    print("Length of refined + full_text = ", len(refined_query_full_text_res))

    for obj in original_query_semantic_res:
        obj["source"] = "semantic"

    for obj in refined_query_semantic_res:
        obj["source"] = "semantic"

    for obj in original_query_full_text_res:
        obj["source"] = "full_text"

    for obj in refined_query_full_text_res:
        obj["source"] = "full_text"

    fused_list = []
    if not len(original_query_semantic_res) == 0:
        print("In here")
        fused_list.append(original_query_semantic_res)

    if not len(refined_query_semantic_res) == 0:
        print("In here as well")
        fused_list.append(refined_query_semantic_res)

    if not len(original_query_full_text_res) == 0:
        print("In here as well 2")
        print("Fused list before appending: ", fused_list)
        fused_list.append(original_query_full_text_res)

    if not len(refined_query_full_text_res) == 0:
        print("In here as well 3")
        print("Fused list before appending: ", fused_list)
        fused_list.append(refined_query_full_text_res)

    print("Fused list length: ", len(fused_list))

    fused_results = reciprocal_rank_fusion(fused_list, top_k)

    # print(fused_results[0])
    # print("Final results received. Now dance")
    return apply_relative_threshold(fused_results, relative_threshold)[: max_results]


def scale_score(score):
    return score * 100
