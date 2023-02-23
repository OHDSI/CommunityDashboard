import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ScanLog, ScanLogsService } from '../scan-logs.service';

@Component({
  selector: 'lib-test',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './test.component.html',
  styleUrls: ['./test.component.css']
})
export class TestComponent {

  data = this.scanLogsService.cache
  data2 = this.scanLogsService.cache

  constructor(
    private scanLogsService: ScanLogsService
  ) {
  }
}
