import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ScanLog, ScanLogsService } from '../scan-logs.service';
import { map } from 'rxjs';

@Component({
  selector: 'lib-test',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './test.component.html',
  styleUrls: ['./test.component.css']
})
export class TestComponent {

  data = this.scanLogsService.cache.pipe(
    map((s: any) => JSON.stringify(s))
  )

  constructor(
    private scanLogsService: ScanLogsService
  ) {
  }
}
