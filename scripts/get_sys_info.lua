local cjson = require("cjson")

--Path to sys files
local batt_path = "/sys/class/power_supply/BAT0/capacity"
local mem_path = "/proc/meminfo"
local cpu_path = ""

local function round(num, numDecimalPlaces)
	local mult = 10 ^ (numDecimalPlaces or 0)
	return math.floor(num * mult + 0.5) / mult
end

local function get_battery_percentage(path)
	local batt_file = io.open(path, "r")
	if not batt_file then
		print("Error: Battery file not found")
		return
	end

	local batt_content = batt_file:read("*a")
	batt_file:close()

	local batt_percentage = string.gsub(batt_content, "\n", "")
	return batt_percentage
end

local function get_mem_usage(path)
	local mem_file = io.open(path, "r")
	if not mem_file then
		print("Error: Meminfo file not found")
		return
	end

	local total_kb = nil
	local free_kb = nil

	for line in mem_file:lines() do
		if string.match(line, "MemTotal:%s+(%d+)") then
			total_kb = string.match(line, "MemTotal:%s+(%d+)")
		end
		if string.match(line, "MemAvailable:%s+(%d+)") then
			free_kb = string.match(line, "MemAvailable:%s+(%d+)")
		end
	end
	mem_file:close()

	total_kb = tonumber(total_kb)
	free_kb = tonumber(free_kb)
	local used_kb = total_kb - free_kb

	local total_gb = round(total_kb * 1024 / 1000000000, 2)
	local used_gb = round(used_kb * 1024 / 1000000000, 2)
	local mem_percentage = round(used_kb / total_kb * 100, 1)

	local mem_info = used_gb .. "/" .. total_gb .. "GB (" .. mem_percentage .. "%)"

	return mem_info
end

--The final sys_info table:
local sys_info = {
	battery = get_battery_percentage(batt_path),
	memory = get_mem_usage(mem_path),
}

--Encoding to JSON for python
local json_output = cjson.encode(sys_info)

print(json_output)
