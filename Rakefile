$venv_dir = '.venv'
$mac_os = `uname -s`.strip == 'Darwin'

desc "Create a Python virtualenv"
task :create_venv do
    raise unless system("virtualenv #{$venv_dir}")
end

task :require_venv_activated do
    unless File.exists? "#{$venv_dir}/bin/activate"
        puts
        puts "Please create a virtual environment."
        puts
        puts "\t$ rake create_venv"
        puts
        raise
    end
    if ENV['VIRTUAL_ENV'] != File.join(Dir.pwd, $venv_dir)
        puts
        puts "Please activate virtualenv."
        puts
        puts "\t$ . #{$venv_dir}/bin/activate"
        puts
        raise
    end
end

desc "Install dependencies for development"
task :install => :require_venv_activated do
    raise unless system("pip install -r requirements_dev.txt")
end

desc "Install dependencies for integration testing"
task :install_integration => :install do
    if $mac_os
        # Homebrew deps for doc gen and integration tests
        raise unless system("brew update")
        raise unless system("brew install chromedriver")
    end

    # Deps for building Fine Uploader for integration tests
    raise unless system("npm install -g grunt-cli")

    if not $mac_os
        puts
        puts "Installation complete."
        puts
        puts "You must install:"
        puts
        puts " - chromedriver"
        puts
        raise
    end
end

desc "Install dependencies for distribution"
task :install_dist => :install do
    if $mac_os
        raise unless system("brew update")
        raise unless system("brew tap phinze/cask")
        raise unless system("brew install brew-cask")
        raise unless system("brew cask install pandoc")
    else
        puts
        puts "You must install:"
        puts
        puts " - pandoc"
        puts
        raise
    end
end

desc "Install a particular version of Fine Uploader for integration testing."
task :install_fine, [:version] do |t, args|
    raise unless system("./fine-uploader-build.sh #{args.version}")
end

def command_is_in_path?(command)
    system("which #{ command} > /dev/null 2>&1")
end

task :test => :require_venv_activated do
    if command_is_in_path?('foreman')
        maybe_foreman_run = 'foreman run'
    else
        maybe_foreman_run = ''
    end
    raise unless system("#{maybe_foreman_run} drf_to_s3/runtests/runtests.py")
end

task :integration => :require_venv_activated do
    unless command_is_in_path?('foreman')
        puts
        puts "Please install `foreman`."
        puts
        puts "Via RubyGems:"
        puts
        puts "\tgem install foreman"
        puts
        puts "Or via Heroku Toolbelt:"
        puts
        puts "\thttps://toolbelt.heroku.com/"
        puts
        raise
    end
    raise unless system("foreman run drf_to_s3/runtests/runtests.py integration")
end

desc "Remove .pyc files"
task :clean do
    system("find . -name '*.pyc' -delete")
end

desc "Remove venv, vendor files, and built distributions"
task :veryclean => :clean do
    system("rm -rf ./#{$venv_dir} vendor/ dist/")
    system("rm -rf drf_to_s3/integration/static/fine-uploader")
end

task :sdist do
    unless command_is_in_path?('pandoc')
        puts
        puts "Please install pandoc."
        puts
        raise
    end
    raise unless system("python setup.py sdist")
end

task :upload do
    unless command_is_in_path?('pandoc')
        puts
        puts "Please install pandoc."
        puts
        raise
    end
    raise unless system("python setup.py sdist upload")
end
