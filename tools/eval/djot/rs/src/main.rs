//! Reads Djot on stdin and prints jotdown's tree as one JSON object:
//! `{"tag", "attrs": [[kind, key, value]], "text", "start", "end", "children"}`.
//! `start`/`end` are byte offsets from `into_offset_iter`: the start event's range
//! start to the end event's range end, which is the container's whole span.
//! No serde, so the dumper pins exactly one dependency.

use jotdown::{AttributeKind, Attributes, Event, Parser};
use std::io::Read;

struct Node {
    tag: String,
    attrs: Vec<(String, String, String)>,
    text: String,
    start: usize,
    end: usize,
    children: Vec<Node>,
}

fn esc(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

fn emit(n: &Node) -> String {
    let attrs: Vec<String> = n
        .attrs
        .iter()
        .map(|(k, key, v)| format!("[{},{},{}]", esc(k), esc(key), esc(v)))
        .collect();
    let kids: Vec<String> = n.children.iter().map(emit).collect();
    format!(
        "{{\"tag\":{},\"attrs\":[{}],\"text\":{},\"start\":{},\"end\":{},\"children\":[{}]}}",
        esc(&n.tag),
        attrs.join(","),
        esc(&n.text),
        n.start,
        n.end,
        kids.join(",")
    )
}

fn variant(debug: String) -> String {
    debug
        .split(|c: char| c == '(' || c == ' ' || c == '{')
        .next()
        .unwrap_or("")
        .to_string()
}

fn flat(attrs: &Attributes) -> Vec<(String, String, String)> {
    attrs
        .into_iter()
        .map(|(kind, value)| match kind {
            AttributeKind::Class => ("class".into(), String::new(), value.to_string()),
            AttributeKind::Id => ("id".into(), String::new(), value.to_string()),
            AttributeKind::Pair { key } => ("pair".into(), key.to_string(), value.to_string()),
            AttributeKind::Comment => ("comment".into(), String::new(), value.to_string()),
        })
        .collect()
}

fn leaf(stack: &mut [Node], tag: &str, attrs: &Attributes, range: std::ops::Range<usize>) {
    stack.last_mut().expect("open").children.push(Node {
        tag: tag.into(),
        attrs: flat(attrs),
        text: String::new(),
        start: range.start,
        end: range.end,
        children: vec![],
    });
}

fn main() {
    let mut src = String::new();
    std::io::stdin().read_to_string(&mut src).expect("stdin");
    let mut stack: Vec<Node> = vec![Node {
        tag: "root".into(),
        attrs: vec![],
        text: String::new(),
        start: 0,
        end: src.len(),
        children: vec![],
    }];
    for (event, range) in Parser::new(&src).into_offset_iter() {
        match event {
            Event::Start(container, attrs) => {
                stack.push(Node {
                    tag: variant(format!("{:?}", container)),
                    attrs: flat(&attrs),
                    text: String::new(),
                    start: range.start,
                    end: range.end,
                    children: vec![],
                });
            }
            Event::End(_) => {
                let mut node = stack.pop().expect("balanced events");
                node.end = range.end;
                let parent = stack.last_mut().expect("root");
                parent.text.push_str(&node.text);
                parent.children.push(node);
            }
            // Two events carry attributes without opening a container: a thematic
            // break, and a specifier jotdown could not attach to anything.
            Event::ThematicBreak(attrs) => leaf(&mut stack, "ThematicBreak", &attrs, range),
            Event::Attributes(attrs) => leaf(&mut stack, "DanglingAttributes", &attrs, range),
            Event::Str(s) => stack.last_mut().expect("open").text.push_str(&s),
            Event::Softbreak | Event::Hardbreak | Event::NonBreakingSpace => {
                stack.last_mut().expect("open").text.push(' ')
            }
            _ => {}
        }
    }
    println!("{}", emit(&stack[0]));
}
