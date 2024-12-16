module Jekyll
  class PhotoGenerator < Generator
    safe true
    priority :high
    
    def generate(site)
      photo_dir = File.join(site.source, 'assets', 'img', 'photos')
      photos = Dir.glob("#{photo_dir}/*.{jpg,png,gif,jpeg,PNG}").map do |file|
        filename = File.basename(file)
        # URL encode the filename to handle special characters
        encoded_filename = ERB::Util.url_encode(filename)
        {
          'src' => "https://gangmuk.github.io/assets/img/photos/#{encoded_filename}",
          'alt' => File.basename(file, File.extname(file)).capitalize,
          'title' => File.basename(file, File.extname(file)).capitalize,
        }
      end
      site.data['photos'] = photos
    end
  end
end


# module Jekyll
#   class PhotoGenerator < Generator
#     safe true
#     priority :high
    
#     def generate(site)
#       photo_dir = File.join(site.source, 'assets', 'img', 'photos')
#       photos = Dir.glob("#{photo_dir}/*.{jpg,png,gif,jpeg}").map do |file|
#         # Use relative path from the root of the site
#         absolute_url = "#{site.config['url']}#{site.config['baseurl']}/assets/img/photos/#{File.basename(file)}"
#         # puts "Found photo: #{file}" # Debug line
#         puts "Generated URL: #{absolute_url}" # Debug line
#         {
#           # 'src' => File.join(site.baseurl, 'assets', 'img', 'photos', File.basename(file)),
#           # 'src' => absolute_url,
#           'src' => "https://gangmuk.github.io/assets/img/photos/#{filename}",
#           'alt' => File.basename(file, File.extname(file)).capitalize,
#           'title' => File.basename(file, File.extname(file)).capitalize,
#         }
#       end
#       puts "Total photos found: #{photos.length}" # Debug line
#       site.data['photos'] = photos
#     end
#   end
# end