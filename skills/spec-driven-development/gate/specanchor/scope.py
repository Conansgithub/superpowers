import glob
import os


def resolve_scope(scope_cell, root):
    """解析作者表 scope 列。'—' = 未圈定(由 index 从 binding 派生),exists=True。
    显式 glob(逗号分隔)展开成相对 root 的文件列表;命中≥1 → exists=True。
    """
    cell = (scope_cell or "").strip()
    if cell == "—" or cell == "":
        return {"globs": [], "files": [], "exists": True}
    globs = [g.strip() for g in cell.split(",") if g.strip()]
    files = []
    for g in globs:
        # 去掉可能的 file::符号 后缀,只用路径部分做 glob
        path_part = g.split("::", 1)[0]
        for hit in glob.glob(os.path.join(root, path_part), recursive=True):
            if os.path.isfile(hit):
                files.append(os.path.relpath(hit, root))
    files = sorted(set(files))
    return {"globs": globs, "files": files, "exists": len(files) > 0}
