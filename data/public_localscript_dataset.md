# Public Sample: Lua Test Tasks

## MWS Octapi

Exported on 2026-03-31 20:17:

## Table of Contents

- 1 Lua Limitations in LowCode
- 1.1 Variables and Data Types
- 1.2 Constructs
- 2 Typical Requests
- 2.1 1. Last Element of an Array
- 2.1.1 User Request
- 2.1.2 Expected Answer
- 2.2 2. Attempt Counter
- 2.2.1 User Request
- 2.2.2 Expected Answer
- 2.3 3. Clearing Values in Variables
- 2.3.1 User Request
- 2.3.2 Expected Answer
- 2.4 4. Bringing Time to ISO Standard
- 2.4.1 User Request
- 2.4.2 Expected Answer
- 2.5 5. Data Type Check
- 2.5.1 User Request
- 2.5.2 Expected Answer
- 2.6 6. Filtering Array Elements
- 2.6.1 User Request
- 2.6.2 Expected Answer
- 2.7 7. Supplementing Existing Code
- 2.7.1 User Request
- 2.7.2 Expected Answer
- 2.8 8. Time Conversion
- 2.8.1 User Request
- 2.8.2 Expected Answer

## 1 Lua Limitations in LowCode

1. **Lua 5** is used.
2. The script is described in JsonString format: **lua{-- action }lua**
3. **Important!** In a Lua script, you **cannot** access variables using JsonPath; instead, you must use direct data access.
4. **All variables declared in LowCode are stored in wf.vars.**
5. Variables received by the schema at startup (from `variables`) are stored in **wf.initVariables**.

## 1.1 Variables and Data Types

The use of basic data types is permitted, such as:

*   **nil** — used to denote the absence of a value.
*   **boolean** — true and false values.
*   **number** — numbers (integers and floating-point).
*   **string** — strings.
*   **array** — arrays. To create a new array during script execution or to declare an existing variable as an array, the following functions are used:
    *   `_utils.array.new()` — to create a new array.
    *   `_utils.array.markAsArray(arr)` — to declare an existing variable as an array.
*   **table** — tables, which in Lua are used to create arrays, lists, associative arrays, and objects.
*   **function** — functions.

## 1.2 Constructs

The following basic constructs are allowed:

*   **if...then...else**
*   **while...do...end**
*   **for...do...end**
*   **repeat...until**

## 2 Typical Requests

## 2.1 1. Last Element of an Array

## 2.1.1 User Request

From the received list of emails, get the last one.

```json
{
  "wf": {
    "vars": {
      "emails": [
        "user1@example.com",
        "user2@example.com",
        "user3@example.com"
      ]
    }
  }
}
```
**Code block 1 Context Example**

## 2.1.2 Expected Answer

```lua
return wf.vars.emails[#wf.vars.emails]
```
**Code block 2 lua**

```json
{
  "lastEmail": "lua{return wf.vars.emails[#wf.vars.emails]}lua"
}
```
**Code block 3 JSON**

## 2.2 2. Attempt Counter

## 2.2.1 User Request

Increment the value of the variable **try_count_n** on each iteration.

```json
{
  "wf": {
    "vars": {
      "try_count_n": 3
    }
  }
}
```
**Code block 4 Context Example**

## 2.2.2 Expected Answer

```lua
return wf.vars.try_count_n + 1
```
**Code block 5 lua**

```json
{
  "try_count_n": "lua{return wf.vars.try_count_n + 1}lua"
}
```
**Code block 6 JSON**

## 2.3 3. Clearing Values in Variables

## 2.3.1 User Request

For the data received from the previous REST request, clear the values of the variables **ID**, **ENTITY_ID**, and **CALL**.

```json
{
  "wf": {
    "vars": {
      "RESTbody": {
        "result": [
          {
            "ID": 123,
            "ENTITY_ID": 456,
            "CALL": "example_call_1",
            "OTHER_KEY_1": "value1",
            "OTHER_KEY_2": "value2"
          },
          {
            "ID": 789,
            "ENTITY_ID": 101,
            "CALL": "example_call_2",
            "EXTRA_KEY_1": "value3",
            "EXTRA_KEY_2": "value4"
          }
        ]
      }
    }
  }
}
```
**Code block 7 Context Example**

## 2.3.2 Expected Answer

```lua
result = wf.vars.RESTbody.result
for _, filteredEntry in pairs(result) do
  for key, value in pairs(filteredEntry) do
    if key ~= "ID" and key ~= "ENTITY_ID" and key ~= "CALL" then
      filteredEntry[key] = nil
    end
  end
end
return result
```
**Code block 8 lua**

```json
{
  "result": "lua{\n\tresult = wf.vars.RESTbody.result\n\tfor _, filteredEntry in pairs(result) do\n\t\tfor key, value in pairs(filteredEntry) do\n\t\t\tif key ~= \"ID\" and key ~= \"ENTITY_ID\" and key ~= \"CALL\" then\n\t\t\t\tfilteredEntry[key] = nil\n\t\t\tend\n\t\tend\n\tend\n\treturn result\n}lua"
}
```

## 2.4 4. Bringing Time to ISO Standard

## 2.4.1 User Request

Convert the time from 'YYYYMMDD' and 'HHMMSS' formats into an ISO 8601 string using Lua.

```json
{
  "wf": {
    "vars": {
      "json": {
        "IDOC": {
          "ZCDF_HEAD": {
            "DELIVERY": "123456789",
            "SUBJECT": "Order Confirmation",
            "DATUM": "20231015",
            "TIME": "153000",
            "STATUS": "Confirmed",
            "ROUTE": "Route 66",
            "ROUTE_TXT": "Main Distribution Route",
            "ZCDF_PACKAGES": [
              {
                "id": "PKG001",
                "number": "EXIDV001",
                "weight": "10",
                "volume": "50",
                "length": "100",
                "width": "50",
                "height": "30",
                "items": [
                  {
                    "sku": "SKU001",
                    "externalId": "MAT001",
                    "quantity": "5",
                    "weight": "2"
                  },
                  {
                    "sku": "SKU002",
                    "externalId": "MAT002",
                    "quantity": "3",
                    "weight": "1"
                  }
                ]
              },
              {
                "id": "PKG002",
                "number": "EXIDV002",
                "weight": "20",
                "volume": "60",
                "length": "120",
                "width": "60",
                "height": "40",
                "items": [
                  {
                    "sku": "SKU003",
                    "externalId": "MAT003",
                    "quantity": "10",
                    "weight": "2"
                  }
                ]
              }
            ]
          }
        }
      }
    }
  }
}
```
**Code block 9 Context Example**

## 2.4.2 Expected Answer

```lua
DATUM = wf.vars.json.IDOC.ZCDF_HEAD.DATUM
TIME = wf.vars.json.IDOC.ZCDF_HEAD.TIME

local function safe_sub(str, start, finish)
    local s = string.sub(str, start, math.min(finish, #str))
    return s ~= "" and s or "00"
end

year = safe_sub(DATUM, 1, 4)
month = safe_sub(DATUM, 5, 6)
day = safe_sub(DATUM, 7, 8)
hour = safe_sub(TIME, 1, 2)
minute = safe_sub(TIME, 3, 4)
second = safe_sub(TIME, 5, 6)

iso_date = string.format(
    '%s-%s-%sT%s:%s:%s.00000Z',
    year, month, day,
    hour, minute, second
)

return iso_date
```
**Code block 10 lua**

```json
{
  "time": "lua{\r\nDATUM = wf.vars.json.IDOC.ZCDF_HEAD.DATUM\r\nTIME = wf.vars.json.IDOC.ZCDF_HEAD.TIME\r\nlocal function safe_sub(str, start, finish)\r\n\tlocal s = string.sub(str, start, math.min(finish, #str))\r\n\treturn s ~= \"\" and s or \"00\"\r\nend \r\nyear = safe_sub(DATUM, 1, 4)\r\nmonth = safe_sub(DATUM, 5, 6)\r\nday = safe_sub(DATUM, 7, 8) \r\nhour = safe_sub(TIME, 1, 2)\r\nminute = safe_sub(TIME, 3, 4)\r\nsecond = safe_sub(TIME, 5, 6) \r\niso_date = string.format(\r\n\t'%s-%s-%sT%s:%s:%s.00000Z',\r\n\tyear, month, day,\r\n\thour, minute, second\r\n) \r\nreturn iso_date \r\n}lua"
}
```
**Code block 11 JSON**

## 2.5 5. Data Type Check

## 2.5.1 User Request

How to transform the data structure so that all **items** in **ZCDF_PACKAGES** are always represented as arrays, even if they were not originally arrays.

```json
{
  "wf": {
    "vars": {
      "json": {
        "IDOC": {
          "ZCDF_HEAD": {
            "ZCDF_PACKAGES": [
              { "items": [{"sku": "A"}, {"sku": "B"}] },
              { "items": {"sku": "C"} }
            ]
          }
        }
      }
    }
  }
}
```
**Code block 12 Context Example**

## 2.5.2 Expected Answer

```lua
function ensureArray(t)
    if type(t) ~= "table" then
        return {t}
    end
    local isArray = true
    for k, v in pairs(t) do
        if type(k) ~= "number" or math.floor(k) ~= k then
            isArray = false
            break
        end
    end
    return isArray and t or {t}
end

function ensureAllItemsAreArrays(objectsArray)
    if type(objectsArray) ~= "table" then
        return objectsArray
    end
    for _, obj in ipairs(objectsArray) do
        if type(obj) == "table" and obj.items then
            obj.items = ensureArray(obj.items)
        end
    end
    return objectsArray
end

return ensureAllItemsAreArrays(wf.vars.json.IDOC.ZCDF_HEAD.ZCDF_PACKAGES)
```
**Code block 13 lua**

```json
{
  "packages": "lua{function ensureArray(t)\r\nif type(t) ~= \"table\" then\r\nreturn {t}\r\nend\r\n local isArray = true\r\nfor k, v in pairs(t) do\r\n if type(k) ~= \"number\" or math.floor(k) ~= k then\r\n isArray = false\r\n break\r\n end\r\n end\r\n return isArray and t or {t}\r\n end\r\n function ensureAllItemsAreArrays(objectsArray)\r\n if type(objectsArray) ~= \"table\" then\r\n return objectsArray\r\n end\r\n for _, obj in ipairs(objectsArray) do\r\n if type(obj) == \"table\" and obj.items then\r\n obj.items = ensureArray(obj.items)\r\n end\r\n end\r\n return objectsArray\r\n end return ensureAllItemsAreArrays(wf.vars.json.IDOC.ZCDF_HEAD.ZCDF_PACKAGES)}lua"
}
```
**Code block 14 JSON**

## 2.6 6. Filtering Array Elements

## 2.6.1 User Request

Filter elements from the array to include only those that have values in the **Discount** or **Markdown** fields.

```json
{
  "wf": {
    "vars": {
      "parsedCsv": [
        { "SKU": "A001", "Discount": "10%", "Markdown": "" },
        { "SKU": "A002", "Discount": "", "Markdown": "5%" },
        { "SKU": "A003", "Discount": null, "Markdown": null },
        { "SKU": "A004", "Discount": "", "Markdown": "" }
      ]
    }
  }
}
```
**Code block 15 Context Example**

## 2.6.2 Expected Answer

```lua
local result = _utils.array.new()
local items = wf.vars.parsedCsv

for _, item in ipairs(items) do
    if (item.Discount ~= "" and item.Discount ~= nil) or (item.Markdown ~= "" and item.Markdown ~= nil) then
        table.insert(result, item)
    end
end

return result
```
**Code block 16 lua**

```json
{
  "result": "lua{\nlocal result = _utils.array.new()\nlocal items = wf.vars.parsedCsv\n\nfor _, item in ipairs(items) do\n if (item.Discount ~= \"\" and item.Discount ~= nil) or (item.Markdown ~= \"\" and item.Markdown ~= nil) then\n table.insert(result, item)\n end\nend\n\nreturn result\n}lua"
}
```
**Code block 17 JSON**

## 2.7 7. Supplementing Existing Code

## 2.7.1 User Request

Add a variable with the square of a number.

## 2.7.2 Expected Answer

```json
{
  "num": "lua{return tonumber('5')}lua",
  "squared": "lua{local n = tonumber('5')\nreturn n * n}lua"
}
```

## 2.8 8. Time Conversion

## 2.8.1 User Request

Convert the time in the variable **recallTime** to unix format.

```json
{
  "wf": {
    "initVariables": {
      "recallTime": "2023-10-15T15:30:00+00:00"
    }
  }
}
```
**Code block 18 Context Example**

## 2.8.2 Expected Answer

```lua
local iso_time = wf.initVariables.recallTime
local days_in_month = { 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 }

if not iso_time or not iso_time:match("^%d%d%d%d%-%d%d%-%d%dT") then
    return nil
end

local function is_leap_year(year)
    return (year % 4 == 0 and year % 100 ~= 0) or (year % 400 == 0)
end

local function days_since_epoch(year, month, day)
    local days = 0
    for y = 1970, year - 1 do
        days = days + (is_leap_year(y) and 366 or 365)
    end
    for m = 1, month - 1 do
        days = days + days_in_month[m]
        if m == 2 and is_leap_year(year) then
            days = days + 1
        end
    end
    days = days + (day - 1)
    return days
end

local function parse_iso8601_to_epoch(iso_str)
    if not iso_str then
        error("Date not set (nil)")
    end

    -- Try with milliseconds
    local year, month, day, hour, min, sec, ms, offset_sign, offset_hour, offset_min = 
        iso_str:match("(%d+)-(%d+)-(%d+)T(%d+):(%d+):(%d+)%.(%d+)([+-])(%d+):(%d+)")

    -- If failed, try without milliseconds
    if not year then
        year, month, day, hour, min, sec, offset_sign, offset_hour, offset_min = 
            iso_str:match("(%d+)-(%d+)-(%d+)T(%d+):(%d+):(%d+)([+-])(%d+):(%d+)")
        ms = 0
    end

    if not year then
        error("Unable to parse date: " .. tostring(iso_str))
    end

    year = tonumber(year)
    month = tonumber(month)
    day = tonumber(day)
    hour = tonumber(hour)
    min = tonumber(min)
    sec = tonumber(sec)
    ms = tonumber(ms) or 0
    offset_hour = tonumber(offset_hour)
    offset_min = tonumber(offset_min)

    local total_days = days_since_epoch(year, month, day)
    local total_seconds = total_days * 86400 + hour * 3600 + min * 60 + sec
    local offset_seconds = offset_hour * 3600 + offset_min * 60

    if offset_sign == "-" then
        offset_seconds = -offset_seconds
    end

    return total_seconds - offset_seconds
end

local epoch_seconds = parse_iso8601_to_epoch(iso_time)
return epoch_seconds
```

```json
{
  "unix_time": "lua{\n\tlocal iso_time = wf.initVariables.recallTime\n\tlocal days_in_month = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31}\n\tif not iso_time or not iso_time:match(\"^%d%d%d%d%-%d%d%-%d%dT\") then\n\t\treturn nil\n\tend\n\tlocal function is_leap_year(year)\n\t\treturn (year % 4 == 0 and year % 100 ~= 0) or (year % 400 == 0)\n\tend\n\tlocal function days_since_epoch(year, month, day)\n\t\tlocal days = 0\n\t\tfor y = 1970, year - 1 do\n\t\t\tdays = days + (is_leap_year(y) and 366 or 365)\n\t\tend\n\t\tfor m = 1, month - 1 do\n\t\t\tdays = days + days_in_month[m]\n\t\t\tif m == 2 and is_leap_year(year) then\n\t\t\t\tdays = days + 1\n\t\t\tend\n\t\tend\n\t\tdays = days + (day - 1)\n\t\treturn days\n\tend\n\tlocal function parse_iso8601_to_epoch(iso_str)\n\t\tif not iso_str then error(\"Date not set (nil)\") end\n\t\tlocal year, month, day, hour, min, sec, ms, offset_sign, offset_hour, offset_min = iso_str:match(\"(%d+)-(%d+)-(%d+)T(%d+):(%d+):(%d+)%.(%d+)([+-])(%d+):(%d+)\")\n\t\tif not year then\n\t\t\tyear, month, day, hour, min, sec, offset_sign, offset_hour, offset_min = iso_str:match(\"(%d+)-(%d+)-(%d+)T(%d+):(%d+):(%d+)([+-])(%d+):(%d+)\")\n\t\t\tms = 0\n\t\tend\n\t\tif not year then error(\"Unable to parse date: \" .. tostring(iso_str)) end\n\t\tyear = tonumber(year); month = tonumber(month); day = tonumber(day)\n\t\thour = tonumber(hour); min = tonumber(min); sec = tonumber(sec)\n\t\tms = tonumber(ms) or 0\n\t\toffset_hour = tonumber(offset_hour); offset_min = tonumber(offset_min)\n\t\tlocal total_days = days_since_epoch(year, month, day)\n\t\tlocal total_seconds = total_days * 86400 + hour * 3600 + min * 60 + sec\n\t\tlocal offset_seconds = offset_hour * 3600 + offset_min * 60\n\t\tif offset_sign == \"-\" then offset_seconds = -offset_seconds end\n\t\treturn total_seconds - offset_seconds\n\tend\n\tlocal epoch_seconds = parse_iso8601_to_epoch(iso_time)\n\treturn epoch_seconds\n}lua"
}
```
**Code block 19 lua**