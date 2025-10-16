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

export default function DateRangePicker() {
  const [startDate, setStartDate] = React.useState<Date>()
  const [endDate, setEndDate] = React.useState<Date>()
  const [open, setOpen] = React.useState(false)

  const handleSelectDate = (selected: Date | { from?: Date; to?: Date } | undefined) => {
    if (!selected) {
      setStartDate(undefined)
      setEndDate(undefined)
      return
    }

    // single Date selection (defensive, though mode="range" usually provides a range object)
    if (selected instanceof Date) {
      const date = selected
      if (!startDate || (startDate && endDate)) {
        setStartDate(date)
        setEndDate(undefined)
      } else if (startDate && !endDate) {
        if (date < startDate) {
          setStartDate(date)
        } else {
          setEndDate(date)
        }
      }
      return
    }

    // range selection: { from, to }
    const { from, to } = selected
    setStartDate(from)
    setEndDate(to)
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
