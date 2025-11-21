#!/usr/bin/env ruby
# Add a user to all projects in OpenProject with a specified role

user_email = ARGV[0] || 'cao.phan@technology.vn'
role_name = ARGV[1] || 'Member'

user = User.find_by(mail: user_email)
if user.nil?
  puts "User not found: #{user_email}"
  exit 1
end

# Get a role with view permissions
role = Role.find_by(name: role_name)
if role.nil?
  puts "Role not found: #{role_name}"
  puts "Available roles: #{Role.pluck(:name).join(', ')}"
  exit 1
end

puts "User: #{user.mail} (ID: #{user.id})"
puts "Role: #{role.name} (ID: #{role.id})"

# Get all projects
projects = Project.all
puts "Found #{projects.count} projects"

# Add user as member to all projects
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
puts "Done!"

