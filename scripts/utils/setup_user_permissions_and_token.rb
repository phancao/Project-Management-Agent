#!/usr/bin/env ruby
# Setup user permissions and generate API token
# Usage: setup_user_permissions_and_token.rb <user_email> [role_name]

user_email = ARGV[0] || 'cao.phan@galaxytechnology.vn'
role_name = ARGV[1] || 'Member'

user = User.find_by(mail: user_email)
if user.nil?
  puts "User not found: #{user_email}"
  exit 0  # Exit gracefully if user doesn't exist
end

puts "User found: #{user.mail} (ID: #{user.id})"

# Get a role with view permissions
role = Role.find_by(name: role_name)
if role.nil?
  puts "Role not found: #{role_name}"
  puts "Available roles: #{Role.pluck(:name).join(', ')}"
  exit 1
end

# Get all projects
projects = Project.all
total_projects = projects.count
puts "Total projects: #{total_projects}"

# Check current memberships
current_memberships = Member.where(user_id: user.id).count
puts "Current project memberships: #{current_memberships}"

# Add user as member to all projects if needed
if current_memberships < total_projects
  added = 0
  skipped = 0
  projects.each do |project|
    # Check if member already exists
    member = Member.find_by(user_id: user.id, project_id: project.id)
    if member.nil?
      # Create member with role assigned
      member = Member.new(user_id: user.id, project_id: project.id)
      member.roles << role
      member.save!
      added += 1
    else
      # Add role if not already assigned
      unless member.roles.include?(role)
        member.roles << role
        member.save!
        added += 1
      else
        skipped += 1
      end
    end
  end
  puts "Added/updated: #{added} project memberships"
  puts "Skipped (already exists): #{skipped} project memberships"
else
  puts "User already has access to all #{total_projects} projects"
end

# Generate API token for the user
puts ""
puts "Generating API token..."
begin
  # Delete existing API tokens for this user (optional - comment out if you want to keep old tokens)
  # Token::API.where(user_id: user.id).destroy_all
  
  # Create new API token
  token = ::Token::API.create!(user: user)
  token_value = token.plain_value
  
  puts "✓ API token generated successfully"
  puts ""
  puts "=" * 60
  puts "USER API TOKEN"
  puts "=" * 60
  puts "Email: #{user.mail}"
  puts "Login: #{user.login}"
  puts "Token: #{token_value}"
  puts ""
  puts "Base64 encoded (for Authorization header):"
  puts "  echo -n 'apikey:#{token_value}' | base64"
  puts "=" * 60
rescue => e
  puts "⚠ Failed to generate API token: #{e.message}"
  exit 1
end

