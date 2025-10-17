"use client"

import * as React from "react"
import { format } from "date-fns"
import { Calendar as CalendarIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

import { DateRange } from "react-day-picker"

export default function DateRangePicker({ date, onDateChange }: { date?: DateRange; onDateChange?: (date: DateRange | undefined) => void }) {
  const [startDate, setStartDate] = React.useState<Date | undefined>(date?.from)
  const [endDate, setEndDate] = React.useState<Date | undefined>(date?.to)
  const [open, setOpen] = React.useState(false)

  // Update internal state when external date changes
  React.useEffect(() => {
    setStartDate(date?.from)
    setEndDate(date?.to)
  }, [date?.from, date?.to])

  const handleSelectDate = (selected: DateRange | undefined) => {
    setStartDate(selected?.from)
    setEndDate(selected?.to)
    onDateChange?.(selected)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn("w-[240px] justify-start text-left font-normal")}
          onClick={() => setOpen(!open)}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {startDate && endDate
            ? `${format(startDate, "MMM dd, yyyy")} – ${format(endDate, "MMM dd, yyyy")}`
            : "Select date range"}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto overflow-hidden p-0" align="start">
        <Calendar
          mode="range"
          selected={{ from: startDate, to: endDate }}
          onSelect={handleSelectDate}
        />
      </PopoverContent>
    </Popover>
  )
}
