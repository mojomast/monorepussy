Gem::Specification.new do |spec|
  spec.name          = "test-gem"
  spec.version       = "1.0.0"
  spec.summary       = "A test gem"

  spec.add_dependency "rails", "~> 7.0"
  spec.add_dependency "pg", "~> 1.5"
  spec.add_dependency "sidekiq", "~> 7.0"
  spec.add_development_dependency "rspec", "~> 3.12"
  spec.add_development_dependency "rubocop", "~> 1.50"
end
