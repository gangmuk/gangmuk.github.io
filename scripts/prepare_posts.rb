#!/usr/bin/env ruby
# scripts/prepare_posts.rb
#
# Pre-build step: for each _posts/SLUG/post.md found:
#   1. Generate _posts/SLUG.md (flat, Jekyll-compatible) with identical content
#   2. Copy all non-.md assets from _posts/SLUG/ to assets/posts/SLUG/
#   3. Rewrite relative image paths in the generated file
#
# The generated _posts/SLUG.md files are transient (gitignored, never committed).

require 'fileutils'

POSTS_DIR     = File.expand_path('../_posts', __dir__)
GENERATED_DIR = File.join(POSTS_DIR, 'generated_for_live_mode')
ASSETS_DIR    = File.expand_path('../assets/posts', __dir__)

FileUtils.rm_rf(GENERATED_DIR)
FileUtils.mkdir_p(GENERATED_DIR)
FileUtils.mkdir_p(ASSETS_DIR)

Dir.glob(File.join(POSTS_DIR, '{blog,notes}', '*', 'post.md')).sort.each do |post_md|
  slug_dir  = File.dirname(post_md)
  slug      = File.basename(slug_dir)
  out_file  = File.join(GENERATED_DIR, "#{slug}.md")
  asset_dst = File.join(ASSETS_DIR, slug)

  # 1. Copy assets (all non-.md files), preserving relative paths under SLUG/
  Dir.glob(File.join(slug_dir, '**', '*')).each do |src|
    next if File.directory?(src)
    next if src.end_with?('.md')
    next if File.basename(src).start_with?('.')

    rel = src.sub("#{slug_dir}/", '')
    dst = File.join(asset_dst, rel)
    FileUtils.mkdir_p(File.dirname(dst))
    FileUtils.cp(src, dst)
  end

  # 2. Read content and rewrite relative image references
  content = File.read(post_md)

  # Markdown: ![alt](./image.png) or ![alt](image.png)  →  ![alt](/assets/posts/SLUG/image.png)
  content = content.gsub(/!\[([^\]]*)\]\((?!https?:\/\/)(?!\/)\.?\/?([^)]+)\)/) do
    "![#{$1}](/assets/posts/#{slug}/#{$2})"
  end

  # HTML img src="./image.png" or src="image.png"  →  src="/assets/posts/SLUG/image.png"
  content = content.gsub(/(<img\b[^>]*\bsrc=)(["'])(?!https?:\/\/)(?!\/)\.?\/?([^"']+)\2/) do
    "#{$1}#{$2}/assets/posts/#{slug}/#{$3}#{$2}"
  end

  # 3. Write generated flat .md
  File.write(out_file, content)
  puts "Generated: #{out_file}"
end

# --- Coffee log posts ---
# Find *-polished-en.md files in _posts/coffee_log/, pair with *-polished-ko.md,
# and generate a combined bilingual post.
COFFEE_DIR = File.join(POSTS_DIR, 'coffee_log')

if File.directory?(COFFEE_DIR)
  Dir.glob(File.join(COFFEE_DIR, '*-polished-en.md')).sort.each do |en_file|
    ko_file = en_file.sub('-polished-en.md', '-polished-ko.md')
    next unless File.exist?(ko_file)

    en_content = File.read(en_file)
    ko_content = File.read(ko_file)

    # Parse title from first line
    title = en_content.lines.first.strip

    # Parse date from "from YYYY.MM.DD" line
    date_match = en_content.match(/from\s+(\d{4})\.(\d{2})\.(\d{2})/)
    next unless date_match
    date = "#{date_match[1]}-#{date_match[2]}-#{date_match[3]}"

    # Build slug from the base filename
    base = File.basename(en_file, '-polished-en.md')
    slug = "#{date}-#{base.downcase.gsub(/[^a-z0-9]+/, '-').gsub(/-+$/, '')}"

    # Strip the first line (title) from both — it's in the front matter now
    en_body = en_content.lines.drop(1).join
    ko_body = ko_content.lines.drop(1).join

    # Generate combined post
    combined = <<~POST
      ---
      layout: post
      title: "#{title}"
      date: #{date}
      category: coffee
      tags: [#{title.split(',').map(&:strip).reject(&:empty?).map { |t| t.gsub('"', '\\"') }.join(', ')}]
      languages: [ko, en]
      default_lang: en
      original_lang: ko
      ---

      <div class="lang-content" data-lang="en" markdown="1">
      #{en_body}
      </div>

      <div class="lang-content" data-lang="ko" style="display:none;" markdown="1">
      #{ko_body}
      </div>
    POST

    out_file = File.join(GENERATED_DIR, "#{slug}.md")
    File.write(out_file, combined.gsub(/^      /, ''))
    puts "Generated (coffee): #{out_file}"
  end
end
