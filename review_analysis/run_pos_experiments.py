"""Compare four POS policies through the shared TF-IDF and EOM pipeline."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from pythainlp.corpus import thai_stopwords

from review_analysis import analyze_tfidf as tfidf
from review_analysis import cluster_terms as cluster
from review_analysis.pos_rules import CORPUS, ENGINE, MODES, WordNetLexicon, tag_tokens
from review_analysis.pos_wordnet_review import occurrence_rows, write_review
from review_analysis.merge_clusters import check_excel_lock
from review_analysis.review_input import (
    checksum, duplicate_review_ids, load_records, write_record_manifest,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("all", *MODES), default="all")
    parser.add_argument("--input", type=Path, default=tfidf.DEFAULT_INPUT)
    parser.add_argument(
        "--output-dir", type=Path, default=tfidf.OUTPUTS_DIR,
        help="โฟลเดอร์รากของผลแต่ละโหมด (default: outputs เดิม)",
    )
    parser.add_argument("--min-df", type=tfidf.positive_int, default=2)
    parser.add_argument("--sort-by", choices=("document_frequency", "tfidf"), default="document_frequency")
    parser.add_argument("--token-examples", type=tfidf.nonnegative_int, default=2)
    parser.add_argument("--device", default="auto")
    return parser.parse_args(argv)


def reserve_outputs(modes, root=None):
    """Reuse fixed mode directories; result files are overwritten on reruns."""
    root = tfidf.OUTPUTS_DIR if root is None else Path(root)
    root.mkdir(parents=True, exist_ok=True)
    paths = {}
    for mode in modes:
        paths[mode] = root / mode
        paths[mode].mkdir(exist_ok=True)
    return paths


def report_examples(reviews, record_ids, documents, tagged, stopwords, modes, count, lexicon=None):
    """Use identical input indices and original adjacent pairs across policies."""
    identifiers = record_ids if record_ids is not None else list(range(1, len(reviews) + 1))
    label = "Record" if record_ids is not None else "Input"
    for index, (review, record_id, tokens, tags) in enumerate(zip(reviews, identifiers, documents, tagged), 1):
        if index > count:
            break
        print(f"\n[{label} {record_id}] {review}")
        print("token/POS:", list(zip(tokens, tags)))
        for mode in modes:
            reasons = tfidf.token_decisions(tokens, stopwords, mode, tags, lexicon)
            print(mode, "occurrences:", [(i, t, tags[i], r) for i, (t, r) in enumerate(zip(tokens, reasons)) if r != "space"])
            # Form pairs on the original sequence, ignoring ordinary spaces only.
            # Rejected tokens remain present; never manufacture a bridged pair.
            indices = [i for i, t in enumerate(tokens) if tfidf.classify_token(t, stopwords) != "space"]
            pairs = [(tokens[a], tokens[b], "เก็บ" if reasons[a] == reasons[b] == "usable" else "ตัด", reasons[a], reasons[b]) for a, b in zip(indices, indices[1:])]
            print(mode, "bigram ก่อน min_df:", pairs)


def cluster_result(candidates, args):
    """Empty input gives no groups; too-small input stays pending review."""
    if len(candidates) < args.min_cluster_size:
        print(f"candidate {len(candidates)}: ไม่พอสำหรับ clustering; ไม่มีการสร้างกลุ่มปกติ")
        return cluster.build_cluster_rows(candidates, [-1] * len(candidates))
    cluster.set_reproducible_seed(args.seed)
    embeddings = cluster.encode_terms(candidates, args.model_name, args.model_revision, args.device, args.batch_size)
    labels, _ = cluster.cluster_embeddings(
        embeddings, min_cluster_size=args.min_cluster_size, min_samples=args.min_samples,
        cluster_selection_epsilon=args.cluster_selection_epsilon,
        cluster_selection_method="eom",
        min_membership_probability=args.min_membership_probability,
    )
    return cluster.build_cluster_rows(candidates, labels)


def main(argv=None):
    args = parse_args(argv)
    print("ปิด Excel ก่อนรัน; รันซ้ำเขียนทับผลชื่อเดิม ควร Save As ก่อนกรอกแง่มุมเอง", flush=True)
    modes = MODES if args.mode == "all" else (args.mode,)
    try:
        input_before = checksum(args.input)
        records = load_records(args.input)
        reviews = [record.text for record in records]
        record_ids = [record.record_id for record in records]
        is_teacher_excel = args.input.suffix.lower() == ".xlsx"
        output_record_ids = record_ids if is_teacher_excel else None
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("record_id ภายในซ้ำ")
        if is_teacher_excel:
            write_record_manifest(args.output_dir / "input_records.json", records, args.input)
        duplicate_ids = duplicate_review_ids(records)
        print(f"input_sha256_before={input_before}")
        print(f"records={len(records)}; unique_record_ids={len(set(record_ids))}; duplicate_review_ids={len(duplicate_ids)}")
        for review_id, count in duplicate_ids.items():
            references = [
                f"{record.record_id}(Excel row {record.source_row})"
                for record in records if record.review_id == review_id
            ]
            print(f"review_id ซ้ำ (เก็บครบ): {review_id!r} จำนวน {count} แถว: {', '.join(references)}")
        documents = [tfidf.tokenize_review(review) for review in reviews]
        needs_evidence = any(mode != "baseline" for mode in modes)
        lexicon = WordNetLexicon() if needs_evidence else None
        tagged = [tag_tokens(tokens) for tokens in documents] if needs_evidence else None
        stopwords = set(thai_stopwords())
        # Preflight selected workbooks before overwriting any result.
        for mode in modes:
            for suffix in ("tfidf", "cluster"):
                check_excel_lock(args.output_dir / mode / f"{mode}_{suffix}.xlsx")
        if needs_evidence:
            print(f"NLTK={tfidf.package_version('nltk')}; WordNet lang=tha; resources=wordnet/omw-1.4; cache=lexical-only", flush=True)
            print("กำลังส่งออก audit ทุก occurrence ที่ผ่านตัวกรองพื้นฐาน", flush=True)
            write_review(args.output_dir / "pos_wordnet_review.xlsx",
                         occurrence_rows(reviews, documents, tagged, stopwords, lexicon, output_record_ids), args.input)
        paths = reserve_outputs(modes, args.output_dir)
        print(f"PyThaiNLP={tfidf.package_version('pythainlp')}; POS engine={ENGINE}; corpus={CORPUS}")
        print(f"input={args.input.resolve()}; N={len(reviews)}; min_df={args.min_df}; sort_by={args.sort_by}")
        if needs_evidence:
            report_examples(reviews, output_record_ids, documents, tagged, stopwords, modes, args.token_examples, lexicon)
        else:
            print("baseline: ไม่โหลด POS/WordNet และไม่เขียนทับ occurrence audit")
        summaries = []
        for mode in modes:
            result = tfidf.analyze_reviews(
                reviews, stopwords, args.min_df, args.sort_by, mode=mode,
                prepared_tokens=documents, prepared_tags=tagged, lexicon=lexicon,
                record_ids=output_record_ids,
            )
            output = paths[mode]
            tfidf.write_csv(output / f"{mode}_tfidf.csv", result.rows)
            tfidf.write_excel(output / f"{mode}_tfidf.xlsx", result.rows)
            config = cluster.parse_args([])
            config.input = output / f"{mode}_tfidf.csv"
            # Read this mode's newly written CSV; empty results have no candidates.
            candidates = cluster.load_candidates(config.input) if result.rows else []
            config.output = output / f"{mode}_cluster.xlsx"
            config.device = cluster.resolve_device(args.device)
            config.cluster_selection_method = "eom"
            cluster.print_parameters(config, config.device)
            groups = cluster_result(candidates, config)
            cluster.write_excel(config.output, groups)
            cluster.validate_written_workbook(config.output, candidates, groups)
            noise = sum(len(g.members) for g in groups if g.group_id == cluster.REVIEW_GROUP_ID)
            normal = [g for g in groups if g.group_id != cluster.REVIEW_GROUP_ID]
            summaries.append((mode, result.unigram_count, result.bigram_count, len(candidates), len(normal), noise, f"{noise / len(candidates):.2%}" if candidates else "N/A", dict(sorted(result.filtered_pos.items()))))
            print(f"\n{mode}: stopwords occurrences={sum(result.filtered_stopwords.values())}; POS/WordNet-filtered occurrences={sum(result.filtered_pos.values())}")
            print("POS/WordNet-filtered by tag:", dict(sorted(result.filtered_pos.items())))
            print("เหตุผลไม่ซ้ำ: กรองตามกฎเดิม/stopwords ก่อน แล้วจึงนับ POS บน token ที่เหลือ")
            if mode == modes[0]:
                tfidf.print_stopword_report(result.filtered_stopwords, stopwords)
            print("ตัวอย่างกลุ่มจริง (กลุ่มใหญ่สุด; ยังต้องตรวจความสอดคล้องด้วยมนุษย์):")
            for group in normal[:20]:
                print(group.group_id, len(group.members), group.member_text.replace("\n", " | "))
            print(f"Output: {output.resolve()}", flush=True)
        print("\nmode\tunigram\tbigram\tcandidates\tgroups\tnoise\tnoise_ratio\tPOS/WordNet-filtered occurrences by tag")
        for summary in summaries:
            print("\t".join(map(str, summary)))
        print("จำนวนคำหรือ noise ที่น้อยกว่าไม่ได้พิสูจน์ว่าคุณภาพ Aspect ดีกว่า; ต้องตรวจบริบทและกลุ่มที่ปะปน")
        input_after = checksum(args.input)
        if input_after != input_before:
            raise ValueError(f"Input checksum เปลี่ยนระหว่างรัน: {args.input}")
        print(f"input_sha256_after={input_after}; Input คงเดิม")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"ข้อผิดพลาด: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
