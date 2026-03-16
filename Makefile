serve:
	ruby scripts/prepare_posts.rb
	bundle exec jekyll serve

build:
	ruby scripts/prepare_posts.rb
	bundle exec jekyll build
