from src.infrastructure.scan_adapter.scanner_adapter import Scanner


def test_should_scan_settlers():
    # Given
    scanner = Scanner(server_speed=1)
    html = """
           <table id="troops">
               <thead>
               <tr>
                   <th colspan="3">Troops:</th>
               </tr>
               </thead>
               <tbody>
               <tr>
                   <td class="ico"><a href="/build.php?id=39#td"><img class="unit uhero" src="/img/x.gif" alt="Hero"></a></td>
                   <td class="num">1</td>
                   <td class="un">Hero</td>
               </tr>
               <tr>
                   <td class="ico"><a href="/build.php?id=39#td"><img class="unit u80" src="/img/x.gif" alt="Settlers"></a></td>
                   <td class="num">6</td>
                   <td class="un">Settlers</td>
               </tr>
               </tbody>
           </table>
           """

    # When
    troops = scanner.scan_troops(html)

    # Then
    expected = {
        "Hero": 1,
        "Settlers": 6
    }
    assert troops == expected, f"Expected {expected} but got {troops}"

def test_should_scan_no_troops():

    # Given
    scanner = Scanner(server_speed=1)
    html = ""

    # When
    troops = scanner.scan_troops(html)

    # Then
    expected = {}
    assert troops == expected, f"Expected {expected} but got {troops}"
