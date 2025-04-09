from pathlib import Path
import astroid


MERMAID_HEADER = "classDiagram"


def is_enum(class_node: astroid.ClassDef) -> bool:
    return any("Enum" in base.as_string() for base in class_node.bases)


def is_dataclass(class_node: astroid.ClassDef) -> bool:
    for decorator in class_node.decorators.nodes if class_node.decorators else []:
        if getattr(decorator, "attrname", None) == "dataclass":
            return True
    return False


def extract_classes(module_path: Path):
    module = astroid.parse(module_path.read_text())
    return [node for node in module.body if isinstance(node, astroid.ClassDef)]


def generate_mermaid(classes):
    lines = [MERMAID_HEADER]

    for cls in classes:
        cls_type = "Enum" if is_enum(cls) else "Dataclass" if is_dataclass(cls) else "Class"
        lines.append(f"    class {cls.name} {{")
        lines.append(f"        <<{cls_type}>>")

        # Attributes
        for node in cls.body:
            if isinstance(node, astroid.Assign):
                for target in node.targets:
                    if isinstance(target, astroid.AssignName):
                        lines.append(f"        {target.name}")
            elif isinstance(node, astroid.AnnAssign) and hasattr(node.target, "name"):
                lines.append(f"        {node.target.name}: {node.annotation.as_string()}")

        lines.append("    }")

        # Inheritance
        for base in cls.bases:
            try:
                base_name = base.as_string()
                lines.append(f"    {base_name} <|-- {cls.name}")
            except AttributeError:
                pass

    return "\n".join(lines)


def main():
    input_path = Path("module/models.py")
    output_path = Path("docs/source/mermaid_models.mmd")

    if not input_path.exists():
        raise FileNotFoundError(f"{input_path} not found")

    print(f"📦 Parsing: {input_path}")
    classes = extract_classes(input_path)

    print(f"🧠 Found {len(classes)} classes")
    mermaid = generate_mermaid(classes)

    output_path.write_text(mermaid)
    print(f"✅ Mermaid diagram written to: {output_path}")


if __name__ == "__main__":
    main()
