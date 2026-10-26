"""Compare four POS policies through the shared TF-IDF and EOM pipeline."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
import uuid

from pythainlp.corpus import thai_stopwords

from review_analysis import analyze_tfidf as tfidf
from review_analysis import cluster_terms as cluster
from review_analysis.pos_rules import CORPUS, ENGINE, MODES, tag_tokens


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("all", *MODES), default="all")
    parser.add_argument("--input", type=Path, default=tfidf.DEFAULT_INPUT)
    parser.add_argument("--min-df", type=tfidf.positive_int, default=2)
    parser.add_argument("--sort-by", choices=("document_frequency", "tfidf"), default="document_frequency")
    parser.add_argument("--token-examples", type=tfidf.nonnegative_int, default=2)
    parser.add_argument("--device", default="auto")
    return parser.parse_args(argv)


def reserve_outputs(modes, root=None):
    """Reserve empty directories; an existing directory is never reused.

    If any requested mode exists, keep the entire comparison in a new run.
    mkdir(exist_ok=False) also fails safely on a concurrent reservation.
    """
    root = tfidf.OUTPUTS_DIR if root is None else Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if any((root / mode).exists() for mode in modes):
        root = root / ("pos_run_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8])
        root.mkdir(exist_ok=False)
        print(f"พบโฟลเดอร์เดิม: ใช้รอบใหม่ {root}")
    paths = {}
    for mode in modes:
        paths[mode] = root / mode
        paths[mode].mkdir(exist_ok=False)
    return paths


def report_examples(reviews, documents, tagged, stopwords, modes, count):
    """Use identical input indices and original adjacent pairs across policies."""
    for index, (review, tokens, tags) in enumerate(zip(reviews, documents, tagged), 1):
        if index > count:
            break
        print(f"\n[Input {index}] {review}")
        print("token/POS:", list(zip(tokens, tags)))
        for mode in modes:
            reasons = tfidf.token_decisions(tokens, stopwords, mode, tags)
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
    modes = MODES if args.mode == "all" else (args.mode,)
    try:
        reviews = tfidf.load_reviews(args.input)
        documents = [tfidf.tokenize_review(review) for review in reviews]
        # Tag complete reviews before either stopword or POS filtering.
        # Baseline analysis ignores these tags; they are for examples only.
        tagged = [tag_tokens(tokens) for tokens in documents]
        stopwords = set(thai_stopwords())
        paths = reserve_outputs(modes)
        print(f"PyThaiNLP={tfidf.package_version('pythainlp')}; POS engine={ENGINE}; corpus={CORPUS}")
        print(f"input={args.input.resolve()}; N={len(reviews)}; min_df={args.min_df}; sort_by={args.sort_by}")
        report_examples(reviews, documents, tagged, stopwords, modes, args.token_examples)
        summaries = []
        for mode in modes:
            result = tfidf.analyze_reviews(
                reviews, stopwords, args.min_df, args.sort_by, mode=mode,
                prepared_tokens=documents, prepared_tags=tagged,
            )
            output = paths[mode]
            tfidf.write_csv(output / f"{mode}_tfidf.csv", result.rows)
            tfidf.write_excel(output / f"{mode}_tfidf.xlsx", result.rows)
            candidates = [cluster.Candidate(i + 2, row["คำ/วลี"], row["ประเภท"]) for i, row in enumerate(result.rows)]
            config = cluster.parse_args([])
            config.input = output / f"{mode}_tfidf.csv"
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
            print(f"\n{mode}: stopwords occurrences={sum(result.filtered_stopwords.values())}; POS-only occurrences={sum(result.filtered_pos.values())}")
            print("POS-only by tag:", dict(sorted(result.filtered_pos.items())))
            print("เหตุผลไม่ซ้ำ: กรองตามกฎเดิม/stopwords ก่อน แล้วจึงนับ POS บน token ที่เหลือ")
            if mode == modes[0]:
                tfidf.print_stopword_report(result.filtered_stopwords, stopwords)
            print("ตัวอย่างกลุ่มจริง (กลุ่มใหญ่สุด; ยังต้องตรวจความสอดคล้องด้วยมนุษย์):")
            for group in normal[:20]:
                print(group.group_id, len(group.members), group.member_text.replace("\n", " | "))
            print(f"Output: {output.resolve()}", flush=True)
        print("\nmode\tunigram\tbigram\tcandidates\tgroups\tnoise\tnoise_ratio\tPOS-only occurrences by tag")
        for summary in summaries:
            print("\t".join(map(str, summary)))
        print("จำนวนคำหรือ noise ที่น้อยกว่าไม่ได้พิสูจน์ว่าคุณภาพ Aspect ดีกว่า; ต้องตรวจบริบทและกลุ่มที่ปะปน")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"ข้อผิดพลาด: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
