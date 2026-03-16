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

POSTS_DIR = File.expand_path('../_posts', __dir__)
ASSETS_DIR = File.expand_path('../assets/posts', __dir__)

FileUtils.mkdir_p(ASSETS_DIR)

Dir.glob(File.join(POSTS_DIR, '*', 'post.md')).sort.each do |post_md|
  slug_dir  = File.dirname(post_md)
  slug      = File.basename(slug_dir)
  out_file  = File.join(POSTS_DIR, "#{slug}.md")
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
