module Jekyll
  class PhotoGenerator < Generator
    safe true
    priority :high
    
    def generate(site)
      photo_dir = File.join(site.source, 'assets', 'img', 'photos')
      photos = Dir.glob("#{photo_dir}/*.{jpg,png,gif,jpeg}").map do |file|
        # Use relative path from the root of the site
        {
          'src' => File.join(site.baseurl, 'assets', 'img', 'photos', File.basename(file)),
          'alt' => File.basename(file, File.extname(file)).capitalize,
          'title' => File.basename(file, File.extname(file)).capitalize,
        }
      end
      site.data['photos'] = photos
    end
  end
end